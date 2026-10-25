"""Tenant-scoped engagement and document endpoints used by the client portal."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel
from sqlalchemy import Select, select
from sqlalchemy.orm import Session, selectinload

from app.auth.dependencies import get_current_user
from app.checklist import ClientStatus
from app.checklist.catalog import load_catalog
from app.database.models import (
    AuditLog,
    CheckJob,
    ChecklistItemInstance,
    Document,
    Engagement,
    EngagementStatus,
    NAReviewState,
    User,
    UserRole,
)
from app.database.session import get_db
from app.documents import DocumentIngestor, get_document_ingestor

router = APIRouter(tags=["engagements"])
DB = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


class APIModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)


class FileView(APIModel):
    id: str
    name: str
    size: int
    uploaded_at: datetime
    sha256: str
    feedback: str | None


class ItemView(APIModel):
    id: str
    request_id: str
    title: str
    description: str
    status: ClientStatus
    reason: str | None
    restricted: bool
    allowed_evidence_types: list[str]
    can_upload: bool
    na_review_state: NAReviewState | None
    representation: str | None
    follow_up: bool
    files: list[FileView]


class SectionView(APIModel):
    id: str
    title: str
    items: list[ItemView]


class ReviewPeriodView(APIModel):
    start: str
    end: str


class EngagementView(APIModel):
    id: str
    firm_name: str
    engagement_type: str
    review_period: ReviewPeriodView
    due_date: str | None
    sections: list[SectionView]
    unassigned_documents: list[FileView] = Field(default_factory=list)


class DocumentView(APIModel):
    id: str
    name: str
    size: int
    sha256: str
    version: str
    status: ClientStatus


Ingestor = Annotated[DocumentIngestor, Depends(get_document_ingestor)]
UploadedFile = Annotated[UploadFile, File()]


def visible_engagements(user: User) -> Select[tuple[Engagement]]:
    stmt = select(Engagement)
    if user.role == UserRole.AUDITOR:
        return stmt.where(Engagement.auditor_id == user.id)
    if not user.firm_id:
        return stmt.where(Engagement.id.is_(None))
    return stmt.where(Engagement.firm_id == user.firm_id)


def _serialize_engagement(engagement: Engagement) -> EngagementView:
    sections: dict[str, SectionView] = {}
    catalog = load_catalog()
    section_titles = {section.id: section.title for section in catalog.sections}
    for item in engagement.items:
        definition = catalog.get(item.item_key)
        if definition is None or (
            not item.applicable and item.na_review_state != NAReviewState.PENDING
        ):
            continue
        section = sections.setdefault(
            definition.section,
            SectionView(id=definition.section, title=section_titles[definition.section], items=[]),
        )
        section.items.append(
            ItemView(
                id=item.id,
                request_id=definition.id,
                title=definition.title,
                description=definition.client_description,
                status=item.status,
                reason=item.client_reason,
                restricted=definition.restricted,
                allowed_evidence_types=definition.allowed_evidence_types,
                can_upload=item.applicable and not definition.restricted,
                na_review_state=item.na_review_state,
                representation=item.representation,
                follow_up=item.follow_up,
                files=[
                    FileView(
                        id=document.id,
                        name=document.original_name,
                        size=document.size_bytes,
                        uploaded_at=document.created_at,
                        sha256=document.sha256,
                        feedback=(
                            {
                                "unreadable": "Please replace with a readable copy.",
                                "wrong_document": "Please provide the requested document.",
                                "wrong_period": "Please provide the review-period document.",
                                "missing_pages": "Please provide a complete copy.",
                            }.get(document.feedback_code)
                        ),
                    )
                    for document in item.documents
                ],
            )
        )
    return EngagementView(
        id=engagement.id,
        firm_name=engagement.firm.name,
        engagement_type=engagement.engagement_type,
        review_period=ReviewPeriodView(
            start=engagement.review_period_start.isoformat(),
            end=engagement.review_period_end.isoformat(),
        ),
        due_date=engagement.due_date.isoformat() if engagement.due_date else None,
        sections=list(sections.values()),
    )


@router.get(
    "/engagements/current",
    response_model=EngagementView,
    response_model_by_alias=True,
)
def current_engagement(user: CurrentUser, db: DB) -> EngagementView:
    engagement = db.scalar(
        visible_engagements(user)
        .where(Engagement.status != EngagementStatus.COMPLETE)
        .options(
            selectinload(Engagement.firm),
            selectinload(Engagement.items).selectinload(ChecklistItemInstance.documents),
        )
        .order_by(Engagement.created_at.desc())
        .limit(1)
    )
    if not engagement:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active engagement")
    db.add(
        AuditLog(
            firm_id=engagement.firm_id,
            actor_id=user.id,
            action="engagement.view",
            entity_type="engagement",
            entity_id=engagement.id,
        )
    )
    for item in engagement.items:
        for document in item.documents:
            db.add(
                AuditLog(
                    firm_id=engagement.firm_id,
                    actor_id=user.id,
                    action="document.view",
                    entity_type="document",
                    entity_id=document.id,
                )
            )
    db.commit()
    view = _serialize_engagement(engagement)
    documents = db.scalars(
        select(Document)
        .where(
            Document.firm_id == engagement.firm_id,
            Document.engagement_id == engagement.id,
            Document.item_instance_id.is_(None),
        )
        .order_by(Document.created_at)
    ).all()
    view.unassigned_documents = [
        FileView(
            id=document.id,
            name=document.original_name,
            size=document.size_bytes,
            uploaded_at=document.created_at,
            sha256=document.sha256,
            feedback=None,
        )
        for document in documents
    ]
    return view


@router.post(
    "/engagements/{engagement_id}/items/{item_id}/documents",
    response_model=DocumentView,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    engagement_id: str,
    item_id: str,
    file: UploadedFile,
    user: CurrentUser,
    db: DB,
    ingestor: Ingestor,
) -> DocumentView:
    engagement = db.scalar(visible_engagements(user).where(Engagement.id == engagement_id))
    if not engagement:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Engagement not found")
    item = db.scalar(
        select(ChecklistItemInstance).where(
            ChecklistItemInstance.id == item_id,
            ChecklistItemInstance.engagement_id == engagement.id,
            ChecklistItemInstance.firm_id == engagement.firm_id,
        )
    )
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Checklist item not found"
        )
    definition = load_catalog().get(item.item_key)
    if definition is None or not item.applicable:
        raise HTTPException(status_code=404, detail="Active request not found")
    if engagement.status in {EngagementStatus.DRAFT, EngagementStatus.COMPLETE}:
        raise HTTPException(status_code=409, detail="Engagement is not accepting uploads")
    if item.restricted or definition.restricted:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This restricted item must be handled directly with the auditor",
        )

    item.accepted_extensions = definition.allowed_evidence_types
    stored = await ingestor.ingest(engagement=engagement, item=item, file=file)
    document = Document(
        firm_id=engagement.firm_id,
        engagement_id=engagement.id,
        item_instance_id=item.id,
        uploaded_by_id=user.id,
        original_name=file.filename or "upload",
        content_type=file.content_type,
        size_bytes=stored.size_bytes,
        egnyte_path=stored.egnyte_path,
        sha256=stored.sha256,
        version=stored.version,
    )
    before = {"status": item.status, "assessment": item.assessment}
    item.status = ClientStatus.CHECKING
    item.assessment = None
    item.client_reason = None
    db.add(document)
    db.flush()
    db.add(CheckJob(firm_id=engagement.firm_id, document_id=document.id))
    db.add(
        AuditLog(
            firm_id=engagement.firm_id,
            actor_id=user.id,
            action="document.created",
            entity_type="checklist_item_instance",
            entity_id=item.id,
            details={
                "document_id": document.id,
                "before": before,
                "after": {"status": item.status, "assessment": None, "sha256": document.sha256},
            },
        )
    )
    db.commit()
    db.refresh(document)
    return DocumentView(
        id=document.id,
        name=document.original_name,
        size=document.size_bytes,
        sha256=document.sha256,
        version=document.version,
        status=item.status,
    )


@router.post(
    "/engagements/{engagement_id}/documents",
    response_model=DocumentView,
    status_code=status.HTTP_201_CREATED,
)
async def upload_unassigned_document(
    engagement_id: str,
    file: UploadedFile,
    user: CurrentUser,
    db: DB,
    ingestor: Ingestor,
) -> DocumentView:
    engagement = db.scalar(visible_engagements(user).where(Engagement.id == engagement_id))
    if not engagement:
        raise HTTPException(status_code=404, detail="Engagement not found")
    if engagement.status in {EngagementStatus.DRAFT, EngagementStatus.COMPLETE}:
        raise HTTPException(status_code=409, detail="Engagement is not accepting uploads")
    stored = await ingestor.ingest(engagement=engagement, item=None, file=file)
    document = Document(
        firm_id=engagement.firm_id,
        engagement_id=engagement.id,
        item_instance_id=None,
        uploaded_by_id=user.id,
        original_name=file.filename or "upload",
        content_type=file.content_type,
        size_bytes=stored.size_bytes,
        egnyte_path=stored.egnyte_path,
        sha256=stored.sha256,
        version=stored.version,
    )
    db.add(document)
    db.flush()
    db.add(CheckJob(firm_id=engagement.firm_id, document_id=document.id))
    db.add(
        AuditLog(
            firm_id=engagement.firm_id,
            actor_id=user.id,
            action="document.created",
            entity_type="document",
            entity_id=document.id,
            details={"engagement_id": engagement.id, "unassigned": True},
        )
    )
    db.commit()
    db.refresh(document)
    return DocumentView(
        id=document.id,
        name=document.original_name,
        size=document.size_bytes,
        sha256=document.sha256,
        version=document.version,
        status=ClientStatus.CHECKING,
    )
