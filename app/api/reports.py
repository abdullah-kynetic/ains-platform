"""Auditor-only report workspace with firm and engagement assignment enforcement."""

from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.api.auditor import DB, CurrentUser, _require_auditor
from app.api.questionnaire import _get_engagement
from app.database.models import Engagement, EngagementReport, User, utcnow
from app.reports.workflow import (
    ReportContent,
    check_version,
    create_report,
    digest,
    record,
    snapshot,
)

router = APIRouter(prefix="/auditor/reports", tags=["reports"])


class CreateReport(BaseModel):
    engagement_id: str


class SaveReport(BaseModel):
    version: int = Field(ge=1)
    content: ReportContent


class ReportVersion(BaseModel):
    version: int = Field(ge=1)


class FinalizeReport(ReportVersion):
    attestation: Literal[True]


def visible(user: User) -> Select[tuple[EngagementReport]]:
    return (
        select(EngagementReport)
        .join(
            Engagement,
            (Engagement.id == EngagementReport.engagement_id)
            & (Engagement.firm_id == EngagementReport.firm_id),
        )
        .where(Engagement.auditor_id == user.id)
    )


def load(
    db: Session, user: User, report_id: str, *, lock: bool = False
) -> EngagementReport:
    _require_auditor(user)
    query = visible(user).where(EngagementReport.id == report_id)
    if lock:
        query = query.with_for_update(of=EngagementReport)
    report = db.scalar(query)
    if report is None:
        raise HTTPException(404, "Report not found")
    return report


def view(report: EngagementReport) -> dict[str, object]:
    return {
        "id": report.id,
        "engagementId": report.engagement_id,
        "firmId": report.firm_id,
        "status": report.status,
        "version": report.version,
        "content": report.content,
        "snapshot": report.snapshot,
        "finalizedAt": report.finalized_at,
        "contentSha256": report.content_sha256,
        "updatedAt": report.updated_at,
    }


@router.get("")
def list_reports(user: CurrentUser, db: DB):
    _require_auditor(user)
    return [
        view(report)
        for report in db.scalars(
            visible(user).order_by(EngagementReport.updated_at.desc()).limit(200)
        )
    ]


@router.post("", status_code=201)
def create(payload: CreateReport, user: CurrentUser, db: DB):
    _require_auditor(user)
    engagement = _get_engagement(db, user, payload.engagement_id)
    report = create_report(db, engagement, user)
    db.commit()
    return view(report)


@router.get("/{report_id}")
def get(report_id: str, user: CurrentUser, db: DB):
    report = load(db, user, report_id)
    return view(report)


@router.patch("/{report_id}")
def save(report_id: str, payload: SaveReport, user: CurrentUser, db: DB):
    report = load(db, user, report_id, lock=True)
    check_version(report, payload.version)
    if report.status != "draft":
        raise HTTPException(409, "Final reports are locked. Reopen to edit.")
    engagement = _get_engagement(db, user, report.engagement_id)
    report.content = payload.content.model_dump()
    report.snapshot = snapshot(db, engagement)
    report.version += 1
    record(db, report, user, "updated")
    db.commit()
    return view(report)


@router.post("/{report_id}/finalize")
def finalize(report_id: str, payload: FinalizeReport, user: CurrentUser, db: DB):
    report = load(db, user, report_id, lock=True)
    check_version(report, payload.version)
    if report.status != "draft":
        raise HTTPException(409, "Report is already final")
    report.status = "final"
    report.finalized_by_id = user.id
    report.finalized_at = utcnow()
    report.content_sha256 = digest(report)
    report.version += 1
    record(db, report, user, "finalized")
    db.commit()
    return view(report)


@router.post("/{report_id}/reopen")
def reopen(report_id: str, payload: ReportVersion, user: CurrentUser, db: DB):
    report = load(db, user, report_id, lock=True)
    check_version(report, payload.version)
    if report.status != "final":
        raise HTTPException(409, "Only a final report can be reopened")
    # The previous final hash remains in the immutable finalization audit event.
    record(db, report, user, "reopened")
    report.status = "draft"
    report.finalized_by_id = None
    report.finalized_at = None
    report.content_sha256 = None
    report.version += 1
    db.commit()
    return view(report)
