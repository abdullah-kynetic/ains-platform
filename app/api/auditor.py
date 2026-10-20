"""Auditor-only evidence queue, finding review, and unsigned draft reports."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.auth.dependencies import get_current_user
from app.checklist import ClientStatus
from app.checks.providers import Citation
from app.config import Settings, get_settings
from app.database.models import (
    AuditLog,
    ChecklistItemInstance,
    Document,
    Engagement,
    FindingDraft,
    NAReviewState,
    ReviewState,
    User,
    UserRole,
)
from app.database.session import get_db
from app.reports import ReportGenerator

router = APIRouter(prefix="/auditor", tags=["auditor"])
DB = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]
AppSettings = Annotated[Settings, Depends(get_settings)]
ReportFormat = Annotated[Literal["docx", "pdf"], Query(alias="format")]


class APIModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)


class CheckView(APIModel):
    id: str
    check_type: str
    status: str
    details: dict[str, object]
    citations: list[dict[str, object]]
    duration_ms: int | None


class EvidenceView(APIModel):
    id: str
    name: str
    egnyte_path: str
    sha256: str
    version: str
    checks: list[CheckView]


class FindingView(APIModel):
    id: str
    title: str
    body: str
    severity: str
    citations: list[dict[str, object]]
    review_state: ReviewState


class QueueItemView(APIModel):
    firm_name: str
    engagement_id: str
    item_id: str
    item_title: str
    client_status: str
    na_review_state: NAReviewState | None
    evidence: list[EvidenceView]
    findings: list[FindingView]


class FindingDecision(APIModel):
    action: Literal["accept", "edit", "reject"]
    title: str | None = Field(default=None, min_length=1, max_length=255)
    body: str | None = Field(default=None, min_length=1, max_length=10_000)
    severity: Literal["low", "moderate", "high", "critical"] | None = None
    citations: list[Citation] | None = None


def _require_auditor(user: User) -> None:
    if user.role != UserRole.AUDITOR:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Auditor access required")


@router.get("/queue", response_model=list[QueueItemView], response_model_by_alias=True)
def auditor_queue(user: CurrentUser, db: DB) -> list[QueueItemView]:
    _require_auditor(user)
    items = db.scalars(
        select(ChecklistItemInstance)
        .join(Engagement, Engagement.id == ChecklistItemInstance.engagement_id)
        .where(
            Engagement.auditor_id == user.id,
            (
                (ChecklistItemInstance.status == ClientStatus.WITH_AUDITOR)
                | (ChecklistItemInstance.na_review_state == NAReviewState.PENDING)
            ),
        )
        .options(
            selectinload(ChecklistItemInstance.engagement).selectinload(Engagement.firm),
            selectinload(ChecklistItemInstance.documents).selectinload(Document.check_results),
        )
        .order_by(ChecklistItemInstance.updated_at)
    ).all()
    queue: list[QueueItemView] = []
    for item in items:
        document_ids = [document.id for document in item.documents]
        findings = (
            db.scalars(
                select(FindingDraft)
                .where(FindingDraft.document_id.in_(document_ids))
                .order_by(FindingDraft.created_at)
            ).all()
            if document_ids
            else []
        )
        queue.append(
            QueueItemView(
                firm_name=item.engagement.firm.name,
                engagement_id=item.engagement_id,
                item_id=item.id,
                item_title=item.title,
                client_status=item.status.value,
                na_review_state=item.na_review_state,
                evidence=[
                    EvidenceView(
                        id=document.id,
                        name=document.original_name,
                        egnyte_path=document.egnyte_path,
                        sha256=document.sha256,
                        version=document.version,
                        checks=[
                            CheckView(
                                id=check.id,
                                check_type=check.check_type,
                                status=check.status,
                                details=check.details,
                                citations=check.citations,
                                duration_ms=check.duration_ms,
                            )
                            for check in document.check_results
                        ],
                    )
                    for document in item.documents
                ],
                findings=[
                    FindingView(
                        id=finding.id,
                        title=finding.title,
                        body=finding.body,
                        severity=finding.severity,
                        citations=finding.citations,
                        review_state=finding.review_state,
                    )
                    for finding in findings
                ],
            )
        )
    return queue


@router.patch("/findings/{finding_id}", response_model=FindingView, response_model_by_alias=True)
def review_finding(
    finding_id: str,
    payload: FindingDecision,
    user: CurrentUser,
    db: DB,
) -> FindingView:
    _require_auditor(user)
    finding = db.scalar(
        select(FindingDraft)
        .join(Document, Document.id == FindingDraft.document_id)
        .join(ChecklistItemInstance, ChecklistItemInstance.id == Document.item_instance_id)
        .join(Engagement, Engagement.id == ChecklistItemInstance.engagement_id)
        .where(FindingDraft.id == finding_id, Engagement.auditor_id == user.id)
    )
    if not finding:
        raise HTTPException(status_code=404, detail="Finding draft not found")
    if payload.action == "edit":
        if payload.title is not None:
            finding.title = payload.title
        if payload.body is not None:
            finding.body = payload.body
        if payload.severity is not None:
            finding.severity = payload.severity
        if payload.citations is not None:
            finding.citations = [citation.model_dump() for citation in payload.citations]
        finding.review_state = ReviewState.EDITED
    elif payload.action == "accept":
        if payload.severity is not None:
            finding.severity = payload.severity
        finding.review_state = ReviewState.ACCEPTED
    else:
        finding.review_state = ReviewState.REJECTED

    if finding.review_state in {ReviewState.ACCEPTED, ReviewState.EDITED} and not finding.citations:
        raise HTTPException(
            status_code=422, detail="Accepted or edited findings require a page citation"
        )
    finding.reviewed_by_id = user.id
    finding.reviewed_at = datetime.now(UTC)
    db.add(
        AuditLog(
            firm_id=finding.firm_id,
            actor_id=user.id,
            action=f"finding.{payload.action}ed",
            entity_type="finding_draft",
            entity_id=finding.id,
            details={"severity": finding.severity},
        )
    )
    db.commit()
    return FindingView(
        id=finding.id,
        title=finding.title,
        body=finding.body,
        severity=finding.severity,
        citations=finding.citations,
        review_state=finding.review_state,
    )


@router.post("/engagements/{engagement_id}/report")
def generate_report(
    engagement_id: str,
    user: CurrentUser,
    db: DB,
    settings: AppSettings,
    output_format: ReportFormat,
) -> Response:
    _require_auditor(user)
    engagement = db.scalar(
        select(Engagement)
        .where(Engagement.id == engagement_id, Engagement.auditor_id == user.id)
        .options(selectinload(Engagement.firm))
    )
    if not engagement:
        raise HTTPException(status_code=404, detail="Engagement not found")
    findings = db.scalars(
        select(FindingDraft)
        .where(
            FindingDraft.engagement_id == engagement.id,
            FindingDraft.firm_id == engagement.firm_id,
            FindingDraft.review_state.in_([ReviewState.ACCEPTED, ReviewState.EDITED]),
        )
        .order_by(FindingDraft.created_at)
    ).all()
    try:
        artifact = ReportGenerator(settings.report_template).generate(
            engagement=engagement, findings=list(findings), output_format=output_format
        )
    except (OSError, ValueError):
        raise HTTPException(status_code=500, detail="Draft report generation failed") from None
    db.add(
        AuditLog(
            firm_id=engagement.firm_id,
            actor_id=user.id,
            action="report.draft_generated",
            entity_type="engagement",
            entity_id=engagement.id,
            details={"format": output_format, "finding_count": len(findings)},
        )
    )
    db.commit()
    return Response(
        artifact.data,
        media_type=artifact.media_type,
        headers={"Content-Disposition": f'attachment; filename="{artifact.filename}"'},
    )
