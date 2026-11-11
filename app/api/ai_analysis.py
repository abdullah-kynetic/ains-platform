"""Auditor-only AI analysis drafts (Stage 3).

The auditor starts a run; an authenticated AI service reads the engagement's uploaded files and
returns DRAFT findings, document flags and suggested client requests, each citing a document and
page. Nothing here is visible to a client: every route is auditor-only, and accepting a draft only
creates an ordinary draft ``Finding`` that still needs the existing human approval and release flow.

The whole feature is off unless AI_ANALYSIS_ENABLED is true; off means 404 on every route.
Order of checks: session (401), auditor role (403), switch (404), engagement scope (404).
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from pathlib import PurePath
from typing import Annotated, Literal, Protocol

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.alias_generators import to_camel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.database.models import (
    AiDraft,
    AiRun,
    AuditLog,
    ChecklistItemInstance,
    Document,
    DocumentItemLink,
    Engagement,
    Finding,
    User,
    UserRole,
)
from app.storage.s3 import S3Storage
from audit_engine.engine import DocInput, run_analysis
from audit_engine.model_client import HttpAdapterClient, ModelClient
from audit_engine.rubric import rubric_items

from .engagements import DB, CurrentUser
from .questionnaire import _get_engagement

router = APIRouter(tags=["ai-analysis"])

MAX_STORED_BYTES = 20 * 1024 * 1024
Kind = Literal["finding", "document_flag", "client_request"]
KIND_PREFIX = {
    "finding": "",
    "document_flag": "Document flag: ",
    "client_request": "Suggested client request: ",
}


class Body(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="forbid")


class View(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class DraftView(View):
    id: str
    run_id: str
    kind: Kind
    item_key: str
    document_id: str
    document_name: str
    page: int
    title: str
    body: str
    model: str
    status: Literal["pending", "accepted", "rejected"]
    edited: bool
    finding_id: str | None
    created_at: datetime


class SkippedView(View):
    document_id: str
    document: str
    code: str
    reason: str


class RunView(View):
    id: str
    created_at: datetime
    documents_analyzed: int
    models: list[str]
    skipped: list[SkippedView]


class AnalysisView(View):
    drafts: list[DraftView]
    last_run: RunView | None


class EditBody(Body):
    title: str = Field(min_length=1, max_length=255)
    body: str = Field(min_length=1, max_length=8000)

    @field_validator("title", "body")
    @classmethod
    def trimmed(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Write some text")
        return value


class DocumentReader(Protocol):
    def __call__(self, document: Document) -> bytes | None: ...


def get_document_reader(settings: Annotated[Settings, Depends(get_settings)]) -> DocumentReader:
    def read(document: Document) -> bytes | None:
        if settings.storage_backend != "s3" or not settings.s3_bucket:
            return None
        if document.size_bytes > MAX_STORED_BYTES:
            return None
        prefix = f"s3://{settings.s3_bucket}/firms/{document.firm_id}/"
        if not document.egnyte_path.startswith(prefix):  # never read another firm's object
            return None
        storage = S3Storage(settings)
        try:
            return asyncio.run(storage.download_file(document.egnyte_path))
        except Exception:  # noqa: BLE001 - becomes the "stored file could not be read" skip
            return None
        finally:
            storage.client.close()

    return read


def get_model_client(settings: Annotated[Settings, Depends(get_settings)]) -> ModelClient | None:
    token = settings.ai_service_token.get_secret_value()
    if not settings.ai_service_url or not token:
        return None
    return HttpAdapterClient(settings.ai_service_url, token)


Reader = Annotated[DocumentReader, Depends(get_document_reader)]
Models = Annotated["ModelClient | None", Depends(get_model_client)]
AppSettings = Annotated[Settings, Depends(get_settings)]


def _gate(user: User, settings: Settings) -> None:
    if user.role != UserRole.AUDITOR:
        raise HTTPException(403, "Auditor access required")
    if not settings.ai_analysis_enabled:
        raise HTTPException(404, "Not found")


def _log(db: Session, engagement: Engagement, user: User, action: str, entity_id: str, **d):
    db.add(
        AuditLog(
            firm_id=engagement.firm_id,
            actor_id=user.id,
            action=action,
            entity_type="ai_draft" if "draft" in action else "ai_run",
            entity_id=entity_id,
            details=d,
        )
    )


def _view(draft: AiDraft, names: dict[str, str]) -> DraftView:
    return DraftView(
        id=draft.id,
        run_id=draft.run_id,
        kind=draft.kind,  # type: ignore[arg-type]
        item_key=draft.item_key,
        document_id=draft.document_id,
        document_name=names.get(draft.document_id, ""),
        page=draft.page,
        title=draft.title,
        body=draft.body,
        model=draft.model,
        status=draft.status,  # type: ignore[arg-type]
        edited=draft.edited,
        finding_id=draft.finding_id,
        created_at=draft.created_at,
    )


def _names(db: Session, engagement: Engagement) -> dict[str, str]:
    rows = db.execute(
        select(Document.id, Document.original_name).where(
            Document.engagement_id == engagement.id, Document.firm_id == engagement.firm_id
        )
    )
    return {doc_id: name for doc_id, name in rows}


def _draft_scope(db: Session, user: User, draft_id: str) -> tuple[Engagement, AiDraft]:
    draft = db.get(AiDraft, draft_id)
    engagement = None
    if draft is not None:
        try:
            engagement = _get_engagement(db, user, draft.engagement_id)
        except HTTPException:
            engagement = None
    # One 404 for a missing draft, another firm's draft, and an unassigned engagement.
    if draft is None or engagement is None or draft.firm_id != engagement.firm_id:
        raise HTTPException(404, "Draft not found")
    return engagement, draft


@router.get(
    "/auditor/engagements/{engagement_id}/ai-analysis",
    response_model=AnalysisView,
    response_model_by_alias=True,
)
def get_analysis(
    engagement_id: str, db: DB, user: CurrentUser, settings: AppSettings
) -> AnalysisView:
    _gate(user, settings)
    engagement = _get_engagement(db, user, engagement_id)
    names = _names(db, engagement)
    drafts = db.scalars(
        select(AiDraft)
        .where(AiDraft.engagement_id == engagement.id, AiDraft.firm_id == engagement.firm_id)
        .order_by(AiDraft.created_at.desc(), AiDraft.id)
    ).all()
    run = db.scalar(
        select(AiRun)
        .where(AiRun.engagement_id == engagement.id, AiRun.firm_id == engagement.firm_id)
        .order_by(AiRun.created_at.desc(), AiRun.id)
        .limit(1)
    )
    return AnalysisView(
        drafts=[_view(d, names) for d in drafts],
        last_run=RunView(
            id=run.id,
            created_at=run.created_at,
            documents_analyzed=run.documents_analyzed,
            models=run.models,
            skipped=[SkippedView(**s) for s in run.skipped],
        )
        if run
        else None,
    )


def _doc_inputs(db: Session, engagement: Engagement, read: DocumentReader) -> list[DocInput]:
    documents = db.scalars(
        select(Document)
        .where(Document.engagement_id == engagement.id, Document.firm_id == engagement.firm_id)
        .order_by(Document.number, Document.created_at)
    ).all()
    items = {
        i.id: i
        for i in db.scalars(
            select(ChecklistItemInstance).where(
                ChecklistItemInstance.engagement_id == engagement.id,
                ChecklistItemInstance.firm_id == engagement.firm_id,
            )
        )
    }
    links: dict[str, set[str]] = {}
    for link in db.scalars(
        select(DocumentItemLink).where(
            DocumentItemLink.engagement_id == engagement.id,
            DocumentItemLink.firm_id == engagement.firm_id,
        )
    ):
        links.setdefault(link.document_id, set()).add(link.item_instance_id)
    inputs: list[tuple[bool, DocInput]] = []
    for doc in documents:
        linked = [items[i] for i in {doc.item_instance_id, *links.get(doc.id, set())} if i in items]
        restricted = any(i.restricted for i in linked)
        linked.sort(key=lambda i: (i.item_key not in rubric_items(), i.position))
        item = linked[0] if linked else None
        # A restricted file's bytes are never even read.
        content = None if restricted else read(doc)
        inputs.append(
            (
                bool(item and item.item_key in rubric_items()),
                DocInput(
                    document_id=doc.id,
                    name=doc.original_name,
                    content=content,
                    item_key=item.item_key if item else "UNASSIGNED",
                    item_title=item.title if item else "Unassigned document",
                    item_text=item.description if item else "",
                    item_restricted=restricted,
                ),
            )
        )
    # Files with a draft rubric first, so a short run covers the core AML items.
    inputs.sort(key=lambda pair: not pair[0])
    return [doc for _, doc in inputs]


@router.post(
    "/auditor/engagements/{engagement_id}/ai-analysis/run",
    response_model=AnalysisView,
    response_model_by_alias=True,
)
def run_ai_analysis(
    engagement_id: str,
    db: DB,
    user: CurrentUser,
    settings: AppSettings,
    read: Reader,
    client: Models,
) -> AnalysisView:
    _gate(user, settings)
    engagement = _get_engagement(db, user, engagement_id)
    if client is None:
        raise HTTPException(503, "The AI service is not configured")
    docs = _doc_inputs(db, engagement, read)
    result = run_analysis(
        docs, client, firm_id=engagement.firm_id, engagement_id=engagement.id, user_id=user.id
    )
    run = AiRun(
        firm_id=engagement.firm_id,
        engagement_id=engagement.id,
        started_by_id=user.id,
        models=result.models,
        documents_analyzed=result.analyzed,
        skipped=result.skipped,
    )
    db.add(run)
    db.flush()
    for d in result.drafts:
        db.add(
            AiDraft(
                firm_id=engagement.firm_id,
                engagement_id=engagement.id,
                run_id=run.id,
                kind=d.kind,
                item_key=d.item_key,
                document_id=d.document_id,
                page=d.page,
                title=d.title,
                body=d.text,
                model=d.model,
            )
        )
    _log(
        db,
        engagement,
        user,
        "ai_analysis.run",
        run.id,
        engagement_id=engagement.id,
        models=result.models,
        documents=len(docs),
        analyzed=result.analyzed,
        skipped=[{"document_id": s["documentId"], "code": s["code"]} for s in result.skipped],
        drafts=len(result.drafts),
    )
    db.commit()
    return get_analysis(engagement_id, db, user, settings)


def _pending(draft: AiDraft) -> None:
    if draft.status != "pending":
        raise HTTPException(409, f"This draft was already {draft.status}")


@router.put("/auditor/ai-drafts/{draft_id}", response_model=DraftView, response_model_by_alias=True)
def edit_draft(
    draft_id: str, body: EditBody, db: DB, user: CurrentUser, settings: AppSettings
) -> DraftView:
    _gate(user, settings)
    engagement, draft = _draft_scope(db, user, draft_id)
    _pending(draft)
    draft.title, draft.body, draft.edited = body.title, body.body, True
    _log(db, engagement, user, "ai_draft.edited", draft.id, engagement_id=engagement.id)
    db.commit()
    return _view(draft, _names(db, engagement))


@router.post(
    "/auditor/ai-drafts/{draft_id}/reject",
    response_model=DraftView,
    response_model_by_alias=True,
)
def reject_draft(draft_id: str, db: DB, user: CurrentUser, settings: AppSettings) -> DraftView:
    _gate(user, settings)
    engagement, draft = _draft_scope(db, user, draft_id)
    _pending(draft)
    draft.status, draft.decided_by_id, draft.decided_at = "rejected", user.id, datetime.now(UTC)
    _log(db, engagement, user, "ai_draft.rejected", draft.id, engagement_id=engagement.id)
    db.commit()
    return _view(draft, _names(db, engagement))


@router.post(
    "/auditor/ai-drafts/{draft_id}/accept",
    response_model=DraftView,
    response_model_by_alias=True,
)
def accept_draft(draft_id: str, db: DB, user: CurrentUser, settings: AppSettings) -> DraftView:
    """Copy the draft into an ordinary DRAFT finding. It still needs approval and release."""
    _gate(user, settings)
    engagement, draft = _draft_scope(db, user, draft_id)
    _pending(draft)
    document = db.get(Document, draft.document_id)
    if document is None or document.engagement_id != engagement.id:
        raise HTTPException(404, "Document not found")
    finding = Finding(
        firm_id=engagement.firm_id,
        engagement_id=engagement.id,
        created_by_id=user.id,
        title=(KIND_PREFIX[draft.kind] + draft.title)[:255],
        condition=draft.body if draft.kind != "client_request" else "",
        recommendation=draft.body if draft.kind == "client_request" else "",
        severity="moderate",
        citations=[{"document": PurePath(document.original_name).name, "page": draft.page}],
        status="draft",
    )
    db.add(finding)
    db.flush()
    draft.status, draft.finding_id = "accepted", finding.id
    draft.decided_by_id, draft.decided_at = user.id, datetime.now(UTC)
    _log(
        db,
        engagement,
        user,
        "ai_draft.accepted",
        draft.id,
        engagement_id=engagement.id,
        finding_id=finding.id,
        edited=draft.edited,
    )
    db.commit()
    return _view(draft, _names(db, engagement))
