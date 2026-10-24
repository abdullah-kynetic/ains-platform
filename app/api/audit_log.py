"""Auditor-only firm audit history and integrity verification."""

from datetime import datetime

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.auditor import DB, CurrentUser, _require_auditor
from app.audit import verify
from app.database.models import (
    AuditLog,
    AuditorTask,
    ChecklistItemInstance,
    Document,
    Engagement,
    FindingDraft,
    User,
)

router = APIRouter(prefix="/auditor/audit-log", tags=["audit-log"])


def authorize(db: Session, user: User, firm_id: str) -> None:
    _require_auditor(user)
    if not db.scalar(
        select(Engagement.id).where(Engagement.firm_id == firm_id, Engagement.auditor_id == user.id)
    ):
        raise HTTPException(404, "Firm not found")
    # A firm chain contains all firm activity; require assignment to every engagement.
    if db.scalar(
        select(Engagement.id).where(
            Engagement.firm_id == firm_id,
            (Engagement.auditor_id != user.id) | Engagement.auditor_id.is_(None),
        )
    ):
        raise HTTPException(403, "Full firm assignment required")


@router.get("")
def read_log(
    user: CurrentUser,
    db: DB,
    firm_id: str,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    action: str | None = None,
    entity_type: str | None = None,
    entity_id: str | None = None,
    actor_id: str | None = None,
    engagement_id: str | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
):
    authorize(db, user, firm_id)
    query = select(AuditLog).where(AuditLog.firm_id == firm_id)
    if engagement_id:
        engagement = db.scalar(
            select(Engagement).where(
                Engagement.id == engagement_id,
                Engagement.firm_id == firm_id,
                Engagement.auditor_id == user.id,
            )
        )
        if not engagement:
            raise HTTPException(404, "Engagement not found")
        targets = [engagement_id]
        for model, column in [
            (ChecklistItemInstance, ChecklistItemInstance.engagement_id),
            (FindingDraft, FindingDraft.engagement_id),
            (AuditorTask, AuditorTask.engagement_id),
        ]:
            targets.extend(
                db.scalars(
                    select(model.id).where(model.firm_id == firm_id, column == engagement_id)
                ).all()
            )
        targets.extend(
            db.scalars(
                select(Document.id)
                .join(ChecklistItemInstance)
                .where(
                    Document.firm_id == firm_id,
                    ChecklistItemInstance.firm_id == firm_id,
                    ChecklistItemInstance.engagement_id == engagement_id,
                )
            ).all()
        )
        query = query.where(AuditLog.entity_id.in_(targets))
    for column, value in [
        (AuditLog.action, action),
        (AuditLog.entity_type, entity_type),
        (AuditLog.entity_id, entity_id),
        (AuditLog.actor_id, actor_id),
    ]:
        if value is not None:
            query = query.where(column == value)
    if since:
        query = query.where(AuditLog.created_at >= since)
    if until:
        query = query.where(AuditLog.created_at <= until)
    rows = db.scalars(
        query.order_by(AuditLog.sequence.desc()).offset(offset).limit(limit + 1)
    ).all()
    return {
        "items": [
            {
                "id": r.id,
                "firm_id": r.firm_id,
                "actor_id": r.actor_id,
                "action": r.action,
                "entity_type": r.entity_type,
                "entity_id": r.entity_id,
                "created_at": r.created_at,
                "ip_address": r.ip_address,
                "sequence": r.sequence,
                "previous_hash": r.previous_hash,
                "row_hash": r.row_hash,
            }
            for r in rows[:limit]
        ],
        "has_more": len(rows) > limit,
    }


@router.get("/verify-chain")
def verify_chain(user: CurrentUser, db: DB, firm_id: str):
    authorize(db, user, firm_id)
    return verify(
        db.scalars(
            select(AuditLog).where(AuditLog.firm_id == firm_id).order_by(AuditLog.sequence)
        ).all()
    )
