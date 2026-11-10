"""Engagement report draft (L2-6e): assembled sections, edits, Word and PDF downloads.

Auditor-only. The draft is assembled on the server from the auditor's own stored entries (see
``app.reports.draft``); edits replace one section's text. Finalizing and signing stay with the
existing report and sign-off routes. The draft contains finding text, so no client route exists.
"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel
from sqlalchemy import select

from app.database.models import AuditLog, EngagementReport, ReportSectionEdit, User, UserRole
from app.reports.draft import assembled_sections, draft_sections, render_docx, render_pdf

from .engagements import DB, CurrentUser
from .questionnaire import _get_engagement

router = APIRouter(tags=["report-draft"])
DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


class View(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class SectionView(View):
    id: str
    title: str
    body: str


class ReportDraftView(View):
    engagement_id: str
    sections: list[SectionView]
    generated_at: datetime


class SectionBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    body: str = Field(max_length=20000)


def _engagement(db, user: User, engagement_id: str):
    if user.role != UserRole.AUDITOR:
        raise HTTPException(403, "Auditor access required")
    return _get_engagement(db, user, engagement_id)


def _view(engagement, sections) -> ReportDraftView:
    return ReportDraftView(
        engagement_id=engagement.id,
        sections=[SectionView(id=s.id, title=s.title, body=s.body) for s in sections],
        generated_at=datetime.now(UTC),
    )


@router.get(
    "/auditor/engagements/{engagement_id}/report-draft",
    response_model=ReportDraftView,
    response_model_by_alias=True,
)
def get_report_draft(engagement_id: str, db: DB, user: CurrentUser) -> ReportDraftView:
    engagement = _engagement(db, user, engagement_id)
    return _view(engagement, draft_sections(db, engagement, user))


@router.put(
    "/auditor/engagements/{engagement_id}/report-draft/sections/{section_id}",
    response_model=SectionView,
    response_model_by_alias=True,
)
def save_section(
    engagement_id: str, section_id: str, payload: SectionBody, db: DB, user: CurrentUser
) -> SectionView:
    engagement = _engagement(db, user, engagement_id)
    if section_id not in {s.id for s in assembled_sections(db, engagement, user)}:
        raise HTTPException(404, "Section not found")
    final = db.scalar(
        select(EngagementReport.id).where(
            EngagementReport.engagement_id == engagement.id,
            EngagementReport.firm_id == engagement.firm_id,
            EngagementReport.status == "final",
        )
    )
    if final is not None:
        raise HTTPException(409, "Final reports are locked. Reopen to edit.")
    row = db.scalar(
        select(ReportSectionEdit).where(
            ReportSectionEdit.engagement_id == engagement.id,
            ReportSectionEdit.firm_id == engagement.firm_id,
            ReportSectionEdit.section_id == section_id,
        )
    )
    if row is None:
        row = ReportSectionEdit(
            firm_id=engagement.firm_id, engagement_id=engagement.id, section_id=section_id
        )
        db.add(row)
    row.body, row.edited_by_id, row.edited_at = payload.body, user.id, datetime.now(UTC)
    db.add(
        AuditLog(
            firm_id=engagement.firm_id,
            actor_id=user.id,
            action="report_draft.section_edited",
            entity_type="engagement",
            entity_id=engagement.id,
            details={"section_id": section_id, "text_length": len(payload.body)},
        )
    )
    db.commit()
    section = next(s for s in draft_sections(db, engagement, user) if s.id == section_id)
    return SectionView(id=section.id, title=section.title, body=section.body)


def _download(engagement_id: str, kind: str, db, user: User) -> Response:
    engagement = _engagement(db, user, engagement_id)
    title = f"AML independent test: {engagement.firm.name}"
    sections = draft_sections(db, engagement, user)
    data, media = (
        (render_docx(title, sections), DOCX)
        if kind == "docx"
        else (render_pdf(title, sections), "application/pdf")
    )
    db.add(
        AuditLog(
            firm_id=engagement.firm_id,
            actor_id=user.id,
            action="report_draft.downloaded",
            entity_type="engagement",
            entity_id=engagement.id,
            details={"format": kind},
        )
    )
    db.commit()
    name = f"report-draft-{engagement.id[:8]}.{kind}"
    return Response(
        data,
        media_type=media,
        headers={
            "Content-Disposition": f'attachment; filename="{name}"',
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.get("/auditor/engagements/{engagement_id}/report-draft/docx")
def download_docx(engagement_id: str, db: DB, user: CurrentUser) -> Response:
    return _download(engagement_id, "docx", db, user)


@router.get("/auditor/engagements/{engagement_id}/report-draft/pdf")
def download_pdf(engagement_id: str, db: DB, user: CurrentUser) -> Response:
    return _download(engagement_id, "pdf", db, user)
