"""Engagement activity, notifications and search (L2-6g). Auditor-only.

All three are computed from the caller's own scope (assigned engagements, ``firm_id`` on every
query). Activity reads the firm audit chain and shows action names only, never entered text.
Notifications are derived on each request; only the read marks are stored. Search matches names
and titles, never document contents, and returns links, not data.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Literal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel
from sqlalchemy import or_, select
from sqlalchemy.orm import selectinload

from app.checklist.catalog import load_catalog
from app.database.models import (
    AuditLog,
    ChecklistItemInstance,
    Document,
    Engagement,
    EngagementSignoff,
    EngagementStatus,
    Finding,
    FindingDraft,
    Invoice,
    NotificationRead,
    ResponseRequest,
    SampleSet,
    User,
    UserRole,
    Workpaper,
)

from .engagements import DB, CurrentUser
from .questionnaire import _get_engagement, visible_engagements

router = APIRouter(tags=["feed"])
WINDOW = timedelta(days=14)
DEADLINE_DAYS = 14


class View(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class ActivityView(View):
    id: str
    engagement_id: str
    at: datetime
    actor: str
    action: str


class NotificationView(View):
    id: str
    at: datetime
    title: str
    detail: str
    href: str
    kind: Literal["deadline", "upload", "finding", "signoff", "invoice"]
    read: bool


class SearchHitView(View):
    id: str
    kind: Literal["Client", "Engagement", "Finding", "Request", "Document"]
    title: str
    detail: str
    href: str


def _auditor(user: User) -> None:
    if user.role != UserRole.AUDITOR:
        raise HTTPException(403, "Auditor access required")


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=UTC)


def _sentence(action: str) -> str:
    text = action.replace(".", " ").replace("_", " ").strip()
    return text[:1].upper() + text[1:] + "."


@router.get(
    "/auditor/engagements/{engagement_id}/activity",
    response_model=list[ActivityView],
    response_model_by_alias=True,
)
def engagement_activity(engagement_id: str, db: DB, user: CurrentUser) -> list[ActivityView]:
    _auditor(user)
    engagement = _get_engagement(db, user, engagement_id)
    scope = {"engagement_id": engagement.id, "firm_id": engagement.firm_id}
    ids = {engagement.id}
    for model in (ChecklistItemInstance, Document, Finding, ResponseRequest, Workpaper, SampleSet):
        ids.update(
            db.scalars(
                select(model.id).where(
                    model.engagement_id == scope["engagement_id"],
                    model.firm_id == scope["firm_id"],
                )
            )
        )
    ids.update(
        db.scalars(
            select(FindingDraft.id).where(
                FindingDraft.engagement_id == engagement.id,
                FindingDraft.firm_id == engagement.firm_id,
            )
        )
    )
    rows = db.execute(
        select(AuditLog, User.name, User.role)
        .outerjoin(User, User.id == AuditLog.actor_id)
        .where(AuditLog.firm_id == engagement.firm_id, AuditLog.entity_id.in_(ids))
        .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        .limit(100)
    ).all()
    return [
        ActivityView(
            id=log.id,
            engagement_id=engagement.id,
            at=log.created_at,
            actor=(
                "System"
                if name is None
                else f"{name} (client)"
                if role == UserRole.CLIENT
                else name
            ),
            action=_sentence(log.action),
        )
        for log, name, role in rows
    ]


def _derive(db, user: User) -> list[NotificationView]:
    engagements = db.scalars(visible_engagements(user).options(selectinload(Engagement.firm))).all()
    if not engagements:
        return []
    by_id = {e.id: e for e in engagements}
    firm_ids = {e.firm_id for e in engagements}
    now = datetime.now(UTC)
    since = now - WINDOW
    out: list[tuple[str, datetime, str, str, str, str]] = []
    for e in engagements:
        if e.due_date and e.status != EngagementStatus.COMPLETE:
            days = (e.due_date - date.today()).days
            if days <= DEADLINE_DAYS:
                when = (
                    f"{-days} day{'s' if days != -1 else ''} overdue"
                    if days < 0
                    else "due today"
                    if days == 0
                    else f"due in {days} day{'s' if days != 1 else ''}"
                )
                out.append(
                    (
                        f"deadline-{e.id}",
                        datetime.combine(e.due_date, datetime.min.time(), tzinfo=UTC),
                        f"{e.firm.name}: report {when}",
                        f"Due {e.due_date.isoformat()}",
                        f"/auditor/engagements/{e.id}",
                        "deadline",
                    )
                )
    for invoice in db.scalars(
        select(Invoice)
        .where(
            Invoice.firm_id.in_(firm_ids),
            Invoice.auditor_id == user.id,
            Invoice.status == "sent",
            Invoice.due_date < date.today(),
        )
        .limit(20)
    ):
        if invoice.amount_paid_cents >= invoice.total_cents:
            continue
        out.append(
            (
                f"invoice-overdue-{invoice.id}",
                datetime.combine(invoice.due_date, datetime.min.time(), tzinfo=UTC),
                f"Invoice KIEN-{invoice.number:04d} is overdue",
                f"Due {invoice.due_date.isoformat()}",
                f"/auditor/invoices/{invoice.id}",
                "invoice",
            )
        )
    uploads = db.execute(
        select(Document, User.role)
        .join(User, User.id == Document.uploaded_by_id)
        .where(
            Document.engagement_id.in_(by_id),
            Document.firm_id.in_(firm_ids),
            Document.created_at >= since,
        )
    ).all()
    for document, role in uploads:
        if role != UserRole.CLIENT or document.engagement_id not in by_id:
            continue
        e = by_id[document.engagement_id]
        if e.firm_id != document.firm_id:
            continue
        out.append(
            (
                f"upload-{document.id}",
                _aware(document.created_at),
                f"{e.firm.name} uploaded a document",
                document.original_name,
                f"/auditor/engagements/{e.id}/documents",
                "upload",
            )
        )
    for rr in db.scalars(
        select(ResponseRequest).where(
            ResponseRequest.engagement_id.in_(by_id),
            ResponseRequest.firm_id.in_(firm_ids),
            ResponseRequest.responded_at.is_not(None),
            ResponseRequest.responded_at >= since,
        )
    ):
        e = by_id[rr.engagement_id]
        out.append(
            (
                f"response-{rr.id}",
                _aware(rr.responded_at),  # type: ignore[arg-type]
                f"{e.firm.name} responded to a request",
                rr.title,
                f"/auditor/engagements/{e.id}/findings",
                "finding",
            )
        )
    for so in db.scalars(
        select(EngagementSignoff).where(
            EngagementSignoff.engagement_id.in_(by_id), EngagementSignoff.firm_id.in_(firm_ids)
        )
    ):
        e = by_id[so.engagement_id]
        if so.reviewer_approved_at and _aware(so.reviewer_approved_at) >= since:
            out.append(
                (
                    f"signoff-reviewed-{e.id}",
                    _aware(so.reviewer_approved_at),
                    f"{e.firm.name}: reviewer approved the file",
                    "Waiting for the partner signature."
                    if so.partner_signed_at is None
                    else "Partner has signed.",
                    f"/auditor/engagements/{e.id}/sign-off",
                    "signoff",
                )
            )
        if so.partner_signed_at and _aware(so.partner_signed_at) >= since:
            out.append(
                (
                    f"signoff-signed-{e.id}",
                    _aware(so.partner_signed_at),
                    f"{e.firm.name}: partner signed the report",
                    "Fingerprint recorded.",
                    f"/auditor/engagements/{e.id}/sign-off",
                    "signoff",
                )
            )
    read = set(
        db.scalars(
            select(NotificationRead.notification_id).where(NotificationRead.user_id == user.id)
        )
    )
    out.sort(key=lambda row: row[1], reverse=True)
    return [
        NotificationView(
            id=i,
            at=at,
            title=title,
            detail=detail,
            href=href,
            kind=kind,  # type: ignore[arg-type]
            read=i in read,
        )
        for i, at, title, detail, href, kind in out[:50]
    ]


@router.get(
    "/auditor/notifications",
    response_model=list[NotificationView],
    response_model_by_alias=True,
)
def list_notifications(db: DB, user: CurrentUser) -> list[NotificationView]:
    _auditor(user)
    return _derive(db, user)


def _mark(db, user: User, ids: list[str]) -> None:
    have = set(
        db.scalars(
            select(NotificationRead.notification_id).where(NotificationRead.user_id == user.id)
        )
    )
    for notification_id in ids:
        if notification_id not in have:
            db.add(NotificationRead(user_id=user.id, notification_id=notification_id))
    db.commit()


@router.post("/auditor/notifications/read-all", status_code=204)
def read_all(db: DB, user: CurrentUser) -> None:
    _auditor(user)
    _mark(db, user, [n.id for n in _derive(db, user) if not n.read])


@router.post("/auditor/notifications/{notification_id}/read", status_code=204)
def read_one(notification_id: str, db: DB, user: CurrentUser) -> None:
    _auditor(user)
    if notification_id not in {n.id for n in _derive(db, user)}:
        raise HTTPException(404, "Notification not found")
    _mark(db, user, [notification_id])


def _like(term: str) -> str:
    escaped = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


@router.get("/auditor/search", response_model=list[SearchHitView], response_model_by_alias=True)
def search(db: DB, user: CurrentUser, q: str = Query(default="", max_length=100)):
    _auditor(user)
    term = q.strip()
    if not term:
        return []
    pattern = _like(term)
    engagements = db.scalars(visible_engagements(user).options(selectinload(Engagement.firm))).all()
    if not engagements:
        return []
    by_id = {e.id: e for e in engagements}
    firm_ids = {e.firm_id for e in engagements}
    hits: list[SearchHitView] = []
    seen_firms: set[str] = set()
    for e in engagements:
        if e.firm_id not in seen_firms and term.lower() in e.firm.name.lower():
            seen_firms.add(e.firm_id)
            hits.append(
                SearchHitView(
                    id=e.firm_id,
                    kind="Client",
                    title=e.firm.name,
                    detail="Client",
                    href=f"/auditor/clients/{e.firm_id}",
                )
            )
    for e in engagements:
        text = f"{e.firm.name} {e.status.value} {e.engagement_type}".lower()
        if term.lower() in text:
            hits.append(
                SearchHitView(
                    id=e.id,
                    kind="Engagement",
                    title=e.firm.name,
                    detail=f"{e.review_period_start.isoformat()} to "
                    f"{e.review_period_end.isoformat()} · {e.status.value.replace('_', ' ')}",
                    href=f"/auditor/engagements/{e.id}",
                )
            )
    for f in db.scalars(
        select(Finding)
        .where(
            Finding.engagement_id.in_(by_id),
            Finding.firm_id.in_(firm_ids),
            or_(
                Finding.title.ilike(pattern, escape="\\"), Finding.rule.ilike(pattern, escape="\\")
            ),
        )
        .limit(10)
    ):
        hits.append(
            SearchHitView(
                id=f.id,
                kind="Finding",
                title=f.title,
                detail=f.rule[:120],
                href=f"/auditor/engagements/{f.engagement_id}/findings",
            )
        )
    first = engagements[0].id
    for r in load_catalog().requests:
        if term.lower() in f"{r.id} {r.title}".lower():
            hits.append(
                SearchHitView(
                    id=r.id,
                    kind="Request",
                    title=f"{r.id} · {r.title}",
                    detail="Checklist request",
                    href=f"/auditor/engagements/{first}/checklist",
                )
            )
    for d in db.scalars(
        select(Document)
        .where(
            Document.engagement_id.in_(by_id),
            Document.firm_id.in_(firm_ids),
            or_(
                Document.original_name.ilike(pattern, escape="\\"),
                Document.number.ilike(pattern, escape="\\"),
            ),
        )
        .limit(10)
    ):
        hits.append(
            SearchHitView(
                id=d.id,
                kind="Document",
                title=d.original_name,
                detail=d.number or "",
                href=f"/auditor/engagements/{d.engagement_id}/documents",
            )
        )
    return hits[:20]
