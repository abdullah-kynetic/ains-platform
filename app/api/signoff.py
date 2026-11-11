"""Independence, reviewer approval, partner signature and client reports (L2-6f).

Each step is a recorded human action. The server owns the rules the screens only display:
the preparer cannot review their own file, only a reviewer or partner of the practice can
approve, only a partner can sign, and signing freezes the report text and computes its SHA-256
fingerprint. Clients get only the signed report with the findings sections removed.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.checklist.catalog import load_catalog
from app.database.models import (
    AuditLog,
    ChecklistItemInstance,
    Engagement,
    EngagementSignoff,
    EngagementStatus,
    Finding,
    SampleItem,
    SampleSet,
    User,
    UserRole,
    Workpaper,
)
from app.reports.draft import draft_sections

from .engagements import DB, CurrentUser
from .findings import _blockers as finding_blockers
from .questionnaire import _get_engagement
from .workpapers import _engagement_for_review

router = APIRouter(tags=["signoff"])

QUESTIONS = [
    "Do any engagement team members hold a financial interest in the client?",
    "Has any team member been employed by or served on the board of the client in the last "
    "24 months?",
    "Do we provide, or have we provided, AML program design or operational services to the client?",
    "Does any team member have a family or close personal relationship with a client officer?",
    "Are our fees contingent on the outcome of the test?",
]
QUESTION_IDS = [f"q{i}" for i in range(1, len(QUESTIONS) + 1)]
Answer = Literal["yes", "no"]
Conclusion = Literal["independent", "safeguards_required", "not_independent"]


class Body(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="forbid")


class View(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class AnswerBody(Body):
    id: str
    question: str | None = None
    answer: Answer | None = None


class IndependenceBody(Body):
    answers: list[AnswerBody] = Field(max_length=len(QUESTIONS))
    conflicts: str = Field(default="", max_length=4000)
    safeguards: str = Field(default="", max_length=4000)


class AnswerView(View):
    id: str
    question: str
    answer: Answer | None


class IndependenceView(View):
    engagement_id: str
    answers: list[AnswerView]
    conflicts: str
    safeguards: str
    conclusion: Conclusion | None
    declared_by: str | None
    declared_at: datetime | None


class ReviewerView(View):
    name: str
    approved_at: datetime | None
    note: str


class PartnerView(View):
    name: str
    signed_at: datetime | None
    fingerprint: str | None


class SignoffView(View):
    engagement_id: str
    reviewer: ReviewerView
    partner: PartnerView
    completed_at: datetime | None


class ReviewBody(Body):
    note: str = Field(default="", max_length=2000)


class PartnerBody(Body):
    typed_name: str = Field(min_length=1, max_length=255)


class ConfirmBody(Body):
    fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")


class PortalSection(View):
    id: str
    title: str
    body: str


class PortalReportView(View):
    id: str
    period: str
    available: bool
    signed_on: str | None
    signed_by: str | None
    fingerprint: str | None
    sections: list[PortalSection]
    # Added in L2-8 (additive): the client's recorded confirmation, which unlocks invoicing.
    confirmed: bool = False
    confirmed_at: datetime | None = None


def _auditor(user: User) -> None:
    if user.role != UserRole.AUDITOR:
        raise HTTPException(403, "Auditor access required")


def _assigned(db: Session, user: User, engagement_id: str) -> Engagement:
    _auditor(user)
    return _get_engagement(db, user, engagement_id)


def _row(db: Session, engagement: Engagement) -> EngagementSignoff:
    row = db.scalar(
        select(EngagementSignoff).where(
            EngagementSignoff.engagement_id == engagement.id,
            EngagementSignoff.firm_id == engagement.firm_id,
        )
    )
    if row is None:
        row = EngagementSignoff(
            firm_id=engagement.firm_id,
            engagement_id=engagement.id,
            independence_answers=[],
        )
        db.add(row)
        db.flush()
    return row


def _name(db: Session, user_id: str | None) -> str | None:
    user = db.get(User, user_id) if user_id else None
    return user.name if user else None


def _log(db: Session, engagement: Engagement, user: User, action: str, **details) -> None:
    db.add(
        AuditLog(
            firm_id=engagement.firm_id,
            actor_id=user.id,
            action=action,
            entity_type="engagement",
            entity_id=engagement.id,
            details=details,
        )
    )


def _independence_view(db: Session, engagement: Engagement, row: EngagementSignoff):
    given = {a["id"]: a.get("answer") for a in row.independence_answers or []}
    return IndependenceView(
        engagement_id=engagement.id,
        answers=[
            AnswerView(id=qid, question=question, answer=given.get(qid))
            for qid, question in zip(QUESTION_IDS, QUESTIONS, strict=True)
        ],
        conflicts=row.conflicts,
        safeguards=row.safeguards,
        conclusion=row.independence_conclusion,  # type: ignore[arg-type]
        declared_by=_name(db, row.declared_by_id),
        declared_at=row.declared_at,
    )


def _signoff_view(db: Session, engagement: Engagement, row: EngagementSignoff) -> SignoffView:
    return SignoffView(
        engagement_id=engagement.id,
        reviewer=ReviewerView(
            name=_name(db, row.reviewer_id) or "",
            approved_at=row.reviewer_approved_at,
            note=row.reviewer_note,
        ),
        partner=PartnerView(
            name=_name(db, row.partner_id) or "",
            signed_at=row.partner_signed_at,
            fingerprint=row.partner_fingerprint,
        ),
        completed_at=row.completed_at,
    )


def _plural(n: int, one: str, many: str) -> str:
    return f"{n} {one if n == 1 else many}"


def _blockers(db: Session, engagement: Engagement, row: EngagementSignoff) -> list[str]:
    scope = {"engagement_id": engagement.id, "firm_id": engagement.firm_id}
    known = {request.id for request in load_catalog().requests}
    items = [
        i
        for i in db.scalars(
            select(ChecklistItemInstance).where(
                ChecklistItemInstance.engagement_id == scope["engagement_id"],
                ChecklistItemInstance.firm_id == scope["firm_id"],
            )
        )
        if i.item_key in known
    ]
    out: list[str] = []
    open_items = sum(1 for i in items if i.conclusion is None)
    if open_items:
        out.append(
            f"{_plural(open_items, 'checklist item has', 'checklist items have')} no conclusion."
        )
    set_ids = [
        s.id
        for s in db.scalars(
            select(SampleSet).where(
                SampleSet.engagement_id == engagement.id, SampleSet.firm_id == engagement.firm_id
            )
        )
    ]
    pending = 0
    if set_ids:
        pending = sum(
            1
            for s in db.scalars(
                select(SampleItem).where(
                    SampleItem.set_id.in_(set_ids), SampleItem.firm_id == engagement.firm_id
                )
            )
            if s.result == "pending"
        )
    if pending:
        out.append(f"{_plural(pending, 'sample item is', 'sample items are')} untested.")
    unreviewed = sum(
        1
        for w in db.scalars(
            select(Workpaper).where(
                Workpaper.engagement_id == engagement.id, Workpaper.firm_id == engagement.firm_id
            )
        )
        if w.reviewed_at is None
    )
    if unreviewed:
        out.append(f"{_plural(unreviewed, 'workpaper needs', 'workpapers need')} review.")
    drafts = sum(
        1
        for f in db.scalars(
            select(Finding).where(
                Finding.engagement_id == engagement.id, Finding.firm_id == engagement.firm_id
            )
        )
        if f.status == "draft" or finding_blockers(db, engagement, f)
    )
    if drafts:
        out.append(f"{_plural(drafts, 'finding is', 'findings are')} still a draft.")
    if row.independence_conclusion in (None, "not_independent"):
        out.append("Independence has not been cleared.")
    return out


@router.get(
    "/auditor/engagements/{engagement_id}/independence",
    response_model=IndependenceView,
    response_model_by_alias=True,
)
def get_independence(engagement_id: str, db: DB, user: CurrentUser) -> IndependenceView:
    _auditor(user)
    engagement = _engagement_for_review(db, user, engagement_id)
    row = _row(db, engagement)
    db.commit()
    return _independence_view(db, engagement, row)


@router.put(
    "/auditor/engagements/{engagement_id}/independence",
    response_model=IndependenceView,
    response_model_by_alias=True,
)
def save_independence(
    engagement_id: str, body: IndependenceBody, db: DB, user: CurrentUser
) -> IndependenceView:
    engagement = _assigned(db, user, engagement_id)
    ids = [a.id for a in body.answers]
    if len(set(ids)) != len(ids) or not set(ids) <= set(QUESTION_IDS):
        raise HTTPException(422, "Unknown or repeated question.")
    row = _row(db, engagement)
    if row.reviewer_approved_at is not None:
        raise HTTPException(409, "The file is approved. Independence can no longer change.")
    given = {a.id: a.answer for a in body.answers}
    answers = [{"id": qid, "answer": given.get(qid)} for qid in QUESTION_IDS]
    complete = all(a["answer"] is not None for a in answers)
    any_yes = any(a["answer"] == "yes" for a in answers)
    conclusion = None
    if complete:
        conclusion = (
            "independent"
            if not any_yes
            else "safeguards_required"
            if body.safeguards.strip()
            else "not_independent"
        )
    row.independence_answers = answers
    row.conflicts, row.safeguards = body.conflicts, body.safeguards
    row.independence_conclusion = conclusion
    row.declared_by_id = user.id if complete else None
    row.declared_at = datetime.now(UTC) if complete else None
    _log(
        db,
        engagement,
        user,
        "independence.recorded",
        conclusion=conclusion,
        answered=sum(1 for a in answers if a["answer"] is not None),
        conflicts_length=len(body.conflicts),
        safeguards_length=len(body.safeguards),
    )
    db.commit()
    return _independence_view(db, engagement, row)


@router.get(
    "/auditor/engagements/{engagement_id}/signoff",
    response_model=SignoffView,
    response_model_by_alias=True,
)
def get_signoff(engagement_id: str, db: DB, user: CurrentUser) -> SignoffView:
    _auditor(user)
    engagement = _engagement_for_review(db, user, engagement_id)
    row = _row(db, engagement)
    db.commit()
    return _signoff_view(db, engagement, row)


@router.get("/auditor/engagements/{engagement_id}/signoff/blockers", response_model=list[str])
def get_blockers(engagement_id: str, db: DB, user: CurrentUser) -> list[str]:
    _auditor(user)
    engagement = _engagement_for_review(db, user, engagement_id)
    row = _row(db, engagement)
    db.commit()
    return _blockers(db, engagement, row)


def _require_open(blockers: list[str]) -> None:
    if blockers:
        raise HTTPException(409, "Resolve the blockers first: " + " ".join(blockers))


@router.post(
    "/auditor/engagements/{engagement_id}/signoff/review",
    response_model=SignoffView,
    response_model_by_alias=True,
)
def approve_as_reviewer(
    engagement_id: str, body: ReviewBody, db: DB, user: CurrentUser
) -> SignoffView:
    _auditor(user)
    engagement = _engagement_for_review(db, user, engagement_id)
    if user.team_role not in {"reviewer", "partner"}:
        raise HTTPException(403, "Only a reviewer or partner can approve the file.")
    if user.id == engagement.auditor_id:
        raise HTTPException(409, "The preparer cannot approve their own file.")
    row = _row(db, engagement)
    if row.reviewer_approved_at is not None:
        raise HTTPException(409, "The file is already approved.")
    _require_open(_blockers(db, engagement, row))
    row.reviewer_id, row.reviewer_note = user.id, body.note.strip()
    row.reviewer_approved_at = datetime.now(UTC)
    _log(db, engagement, user, "signoff.reviewed", note_length=len(row.reviewer_note))
    db.commit()
    return _signoff_view(db, engagement, row)


def fingerprint_of(sections: list[dict[str, str]]) -> str:
    text = "\n\n".join(f"{s['title']}\n{s['body']}" for s in sections)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@router.post(
    "/auditor/engagements/{engagement_id}/signoff/partner",
    response_model=SignoffView,
    response_model_by_alias=True,
)
def partner_sign(engagement_id: str, body: PartnerBody, db: DB, user: CurrentUser) -> SignoffView:
    _auditor(user)
    engagement = _engagement_for_review(db, user, engagement_id)
    if user.team_role != "partner":
        raise HTTPException(403, "Only a partner can sign the report.")
    row = _row(db, engagement)
    if row.partner_signed_at is not None:
        raise HTTPException(409, "The report is already signed.")
    if row.reviewer_approved_at is None:
        raise HTTPException(409, "The second reviewer must approve first.")
    if row.reviewer_id == user.id:
        raise HTTPException(409, "The reviewer cannot also sign as partner.")
    if body.typed_name.strip().casefold() != user.name.strip().casefold():
        raise HTTPException(422, f"Type “{user.name}” exactly to sign.")
    _require_open(_blockers(db, engagement, row))
    sections = [
        {"id": s.id, "title": s.title, "body": s.body} for s in draft_sections(db, engagement, user)
    ]
    row.signed_sections = sections
    row.partner_fingerprint = fingerprint_of(sections)
    row.partner_id, row.partner_signed_at = user.id, datetime.now(UTC)
    _log(
        db,
        engagement,
        user,
        "signoff.partner_signed",
        fingerprint=row.partner_fingerprint,
        section_count=len(sections),
    )
    db.commit()
    return _signoff_view(db, engagement, row)


@router.post(
    "/auditor/engagements/{engagement_id}/complete",
    response_model=SignoffView,
    response_model_by_alias=True,
)
def complete_engagement(engagement_id: str, db: DB, user: CurrentUser) -> SignoffView:
    _auditor(user)
    engagement = _engagement_for_review(db, user, engagement_id)
    if user.id != engagement.auditor_id and user.team_role != "partner":
        raise HTTPException(403, "Only the assigned auditor or a partner can complete it.")
    row = _row(db, engagement)
    if row.partner_signed_at is None:
        raise HTTPException(409, "A partner signature is required to complete the engagement.")
    if row.completed_at is not None:
        raise HTTPException(409, "The engagement is already complete.")
    row.completed_at = datetime.now(UTC)
    engagement.status = EngagementStatus.COMPLETE
    _log(db, engagement, user, "engagement.completed", fingerprint=row.partner_fingerprint)
    db.commit()
    return _signoff_view(db, engagement, row)


@router.get(
    "/engagements/{engagement_id}/signed-report",
    response_model=PortalReportView,
    response_model_by_alias=True,
)
def client_signed_report(engagement_id: str, db: DB, user: CurrentUser) -> PortalReportView:
    """The signed report as the client may see it: no findings sections, and nothing until the
    partner has signed and the engagement is complete."""
    if user.role != UserRole.CLIENT:
        raise HTTPException(403, "Client access required")
    engagement = _get_engagement(db, user, engagement_id)
    row = db.scalar(
        select(EngagementSignoff).where(
            EngagementSignoff.engagement_id == engagement.id,
            EngagementSignoff.firm_id == engagement.firm_id,
        )
    )
    period = f"{engagement.review_period_start:%d %b %Y} to {engagement.review_period_end:%d %b %Y}"
    if row is None or row.partner_signed_at is None or row.completed_at is None:
        return PortalReportView(
            id=engagement.id,
            period=period,
            available=False,
            signed_on=None,
            signed_by=None,
            fingerprint=None,
            sections=[],
        )
    return PortalReportView(
        id=engagement.id,
        period=period,
        available=True,
        signed_on=row.partner_signed_at.date().isoformat(),
        signed_by=_name(db, row.partner_id),
        fingerprint=row.partner_fingerprint,
        confirmed=engagement.report_confirmed_at is not None,
        confirmed_at=engagement.report_confirmed_at,
        sections=[
            PortalSection(id=s["id"], title=s["title"], body=s["body"])
            for s in row.signed_sections or []
            if not s["id"].startswith("finding-")
        ],
    )


@router.post(
    "/engagements/{engagement_id}/signed-report/confirm",
    response_model=PortalReportView,
    response_model_by_alias=True,
)
def confirm_signed_report(
    engagement_id: str, body: ConfirmBody, db: DB, user: CurrentUser
) -> PortalReportView:
    """The client confirms the exact signed report by its fingerprint. Recorded once, audit-logged,
    and it is what lets the auditor issue an invoice for this engagement."""
    if user.role != UserRole.CLIENT:
        raise HTTPException(403, "Client access required")
    engagement = _get_engagement(db, user, engagement_id)
    row = db.scalar(
        select(EngagementSignoff).where(
            EngagementSignoff.engagement_id == engagement.id,
            EngagementSignoff.firm_id == engagement.firm_id,
        )
    )
    if row is None or row.partner_signed_at is None or row.completed_at is None:
        raise HTTPException(404, "No signed report")
    if body.fingerprint != row.partner_fingerprint:
        raise HTTPException(409, "The report changed. Reload it and confirm again.")
    if engagement.report_confirmed_at is None:
        engagement.report_confirmed_at = datetime.now(UTC)
        engagement.report_confirmed_by_id = user.id
        engagement.report_confirmed_sha256 = row.partner_fingerprint
        db.add(
            AuditLog(
                firm_id=engagement.firm_id,
                actor_id=user.id,
                action="report.confirmed",
                entity_type="engagement",
                entity_id=engagement.id,
                details={"fingerprint": row.partner_fingerprint, "flow": "signed_report"},
            )
        )
        db.commit()
    return client_signed_report(engagement_id, db, user)
