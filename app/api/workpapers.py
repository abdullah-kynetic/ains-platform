"""Workpapers and sample sets (L2-6c). Auditor-only; clients never see either.

Every route resolves the engagement through the assigned-auditor filter and queries children by
``firm_id`` and engagement. Conclusions, procedures and sample results are human entries stored as
typed. Review needs a second person: the reviewer cannot be the preparer, and editing a reviewed
workpaper's procedure or conclusion clears the review. Sample items are numbered placeholders
(``ITEM-001``..); picking items from a population file is not built.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.alias_generators import to_camel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.checklist.catalog import load_catalog
from app.database.models import (
    AuditLog,
    ChecklistItemInstance,
    Document,
    Engagement,
    SampleItem,
    SampleSet,
    User,
    UserRole,
    Workpaper,
)

from .engagements import DB, CurrentUser
from .questionnaire import _get_engagement

router = APIRouter(tags=["workpapers"])

Conclusion = Literal["pass", "partial", "fail", "na"]
SampleResult = Literal["pending", "pass", "exception"]
MAX_SAMPLE = 500


class Body(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="forbid")


class View(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class WorkpaperView(View):
    request_id: str
    procedure: str
    evidence_ids: list[str]
    conclusion: Conclusion | None
    preparer: str
    prepared_at: datetime | None
    reviewer: str
    reviewed_at: datetime | None


class WorkpaperBody(Body):
    # The web sends the whole workpaper; the id comes from the path.
    request_id: str | None = None
    procedure: str = Field(max_length=8000)
    evidence_ids: list[str] = Field(default_factory=list, max_length=100)
    conclusion: Conclusion | None = None


class SampleItemView(View):
    id: str
    reference: str
    result: SampleResult
    note: str


class SampleSetView(View):
    id: str
    engagement_id: str
    area: str
    request_id: str | None
    population: int
    sample_size: int
    method: str
    items: list[SampleItemView]


class SampleCreate(Body):
    area: str = Field(min_length=1, max_length=200)
    request_id: str | None = None
    population: int = Field(ge=1, le=10_000_000)
    sample_size: int = Field(ge=1, le=MAX_SAMPLE)
    method: str = Field(min_length=1, max_length=200)

    @field_validator("area", "method")
    @classmethod
    def not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("This field is required")
        return value


class SampleResultBody(Body):
    result: SampleResult
    note: str | None = Field(default=None, max_length=2000)


def _engagement(db: Session, user: User, engagement_id: str) -> Engagement:
    if user.role != UserRole.AUDITOR:
        raise HTTPException(403, "Auditor access required")
    return _get_engagement(db, user, engagement_id)


def _engagement_for_review(db: Session, user: User, engagement_id: str) -> Engagement:
    """The assigned auditor, or a reviewer or partner of the same practice as the assignee.

    Used only to read and review workpapers: an independent second person must be able to see
    the preparer's work without being the engagement's assigned auditor.
    """
    if user.role != UserRole.AUDITOR:
        raise HTTPException(403, "Auditor access required")
    try:
        return _get_engagement(db, user, engagement_id)
    except HTTPException:
        if not user.practice_id or user.team_role not in {"reviewer", "partner"}:
            raise
    engagement = db.scalar(
        select(Engagement)
        .join(User, User.id == Engagement.auditor_id)
        .where(Engagement.id == engagement_id, User.practice_id == user.practice_id)
    )
    if engagement is None:
        raise HTTPException(404, "Engagement not found")
    return engagement


def _log(db: Session, engagement: Engagement, user: User, action: str, entity: str, entity_id, **d):
    db.add(
        AuditLog(
            firm_id=engagement.firm_id,
            actor_id=user.id,
            action=action,
            entity_type=entity,
            entity_id=entity_id,
            details=d,
        )
    )


def _has_request(db: Session, engagement: Engagement, request_id: str) -> bool:
    return (
        db.scalar(
            select(ChecklistItemInstance.id).where(
                ChecklistItemInstance.engagement_id == engagement.id,
                ChecklistItemInstance.firm_id == engagement.firm_id,
                ChecklistItemInstance.item_key == request_id,
            )
        )
        is not None
    )


# --- workpapers --------------------------------------------------------------------------


def _workpapers(db: Session, engagement: Engagement) -> list[WorkpaperView]:
    order = {request.id: index for index, request in enumerate(load_catalog().requests)}
    rows = db.scalars(
        select(Workpaper).where(
            Workpaper.engagement_id == engagement.id, Workpaper.firm_id == engagement.firm_id
        )
    ).all()
    names = {
        user.id: user.name
        for user in db.scalars(
            select(User).where(
                User.id.in_(
                    {r.preparer_id for r in rows} | {r.reviewer_id for r in rows if r.reviewer_id}
                )
            )
        )
    }
    rows.sort(key=lambda row: order.get(row.request_id, len(order)))
    return [
        WorkpaperView(
            request_id=row.request_id,
            procedure=row.procedure,
            evidence_ids=list(row.evidence_ids),
            conclusion=row.conclusion,  # type: ignore[arg-type]
            preparer=names.get(row.preparer_id, ""),
            prepared_at=row.prepared_at,
            reviewer=names.get(row.reviewer_id, "") if row.reviewer_id else "",
            reviewed_at=row.reviewed_at,
        )
        for row in rows
    ]


def _one(db: Session, engagement: Engagement, request_id: str) -> WorkpaperView:
    return next(w for w in _workpapers(db, engagement) if w.request_id == request_id)


@router.get(
    "/auditor/engagements/{engagement_id}/workpapers",
    response_model=list[WorkpaperView],
    response_model_by_alias=True,
)
def list_workpapers(engagement_id: str, db: DB, user: CurrentUser) -> list[WorkpaperView]:
    return _workpapers(db, _engagement_for_review(db, user, engagement_id))


@router.put(
    "/auditor/engagements/{engagement_id}/workpapers/{request_id}",
    response_model=WorkpaperView,
    response_model_by_alias=True,
)
def save_workpaper(
    engagement_id: str, request_id: str, body: WorkpaperBody, db: DB, user: CurrentUser
) -> WorkpaperView:
    engagement = _engagement(db, user, engagement_id)
    if not _has_request(db, engagement, request_id):
        raise HTTPException(404, "Request not found")
    evidence = list(dict.fromkeys(body.evidence_ids))
    if evidence:
        found = set(
            db.scalars(
                select(Document.id).where(
                    Document.id.in_(evidence),
                    Document.engagement_id == engagement.id,
                    Document.firm_id == engagement.firm_id,
                )
            )
        )
        if found != set(evidence):
            raise HTTPException(422, "Evidence must be documents of this engagement")
    row = db.scalar(
        select(Workpaper).where(
            Workpaper.engagement_id == engagement.id,
            Workpaper.firm_id == engagement.firm_id,
            Workpaper.request_id == request_id,
        )
    )
    cleared = False
    if row is None:
        row = Workpaper(
            firm_id=engagement.firm_id,
            engagement_id=engagement.id,
            request_id=request_id,
            preparer_id=user.id,
        )
        db.add(row)
    elif row.reviewed_at is not None and (
        row.procedure != body.procedure or row.conclusion != body.conclusion
    ):
        # A changed procedure or conclusion needs a fresh second look.
        row.reviewer_id, row.reviewed_at, cleared = None, None, True
    row.procedure = body.procedure
    row.evidence_ids = evidence
    row.conclusion = body.conclusion
    row.preparer_id = user.id
    row.prepared_at = datetime.now(UTC)
    db.flush()
    _log(
        db,
        engagement,
        user,
        "workpaper.saved",
        "workpaper",
        row.id,
        request_id=request_id,
        review_cleared=cleared,
    )
    db.commit()
    return _one(db, engagement, request_id)


@router.post(
    "/auditor/engagements/{engagement_id}/workpapers/{request_id}/review",
    response_model=list[WorkpaperView],
    response_model_by_alias=True,
)
def review_workpaper(
    engagement_id: str, request_id: str, db: DB, user: CurrentUser
) -> list[WorkpaperView]:
    engagement = _engagement_for_review(db, user, engagement_id)
    row = db.scalar(
        select(Workpaper).where(
            Workpaper.engagement_id == engagement.id,
            Workpaper.firm_id == engagement.firm_id,
            Workpaper.request_id == request_id,
        )
    )
    if row is None:
        raise HTTPException(404, "Workpaper not found")
    if row.preparer_id == user.id:
        raise HTTPException(409, "A different auditor must review this workpaper.")
    row.reviewer_id = user.id
    row.reviewed_at = datetime.now(UTC)
    _log(db, engagement, user, "workpaper.reviewed", "workpaper", row.id, request_id=request_id)
    db.commit()
    return _workpapers(db, engagement)


# --- samples -----------------------------------------------------------------------------


def _set_view(sample: SampleSet) -> SampleSetView:
    return SampleSetView(
        id=sample.id,
        engagement_id=sample.engagement_id,
        area=sample.area,
        request_id=sample.request_id,
        population=sample.population,
        sample_size=sample.sample_size,
        method=sample.method,
        items=[
            SampleItemView(
                id=item.id,
                reference=item.reference,
                result=item.result,  # type: ignore[arg-type]
                note=item.note,
            )
            for item in sample.items
        ],
    )


def _samples(db: Session, engagement: Engagement) -> list[SampleSetView]:
    sets = db.scalars(
        select(SampleSet)
        .where(SampleSet.engagement_id == engagement.id, SampleSet.firm_id == engagement.firm_id)
        .order_by(SampleSet.created_at, SampleSet.id)
    ).all()
    return [_set_view(sample) for sample in sets]


@router.get(
    "/auditor/engagements/{engagement_id}/samples",
    response_model=list[SampleSetView],
    response_model_by_alias=True,
)
def list_samples(engagement_id: str, db: DB, user: CurrentUser) -> list[SampleSetView]:
    return _samples(db, _engagement(db, user, engagement_id))


@router.post(
    "/auditor/engagements/{engagement_id}/samples",
    response_model=SampleSetView,
    status_code=201,
    response_model_by_alias=True,
)
def create_sample(
    engagement_id: str, body: SampleCreate, db: DB, user: CurrentUser
) -> SampleSetView:
    engagement = _engagement(db, user, engagement_id)
    if body.sample_size > body.population:
        raise HTTPException(422, "The sample cannot be larger than the population")
    if body.request_id is not None and not _has_request(db, engagement, body.request_id):
        raise HTTPException(404, "Request not found")
    sample = SampleSet(
        firm_id=engagement.firm_id,
        engagement_id=engagement.id,
        area=body.area.strip(),
        request_id=body.request_id,
        population=body.population,
        sample_size=body.sample_size,
        method=body.method.strip(),
        created_by_id=user.id,
        items=[
            SampleItem(
                firm_id=engagement.firm_id,
                position=index,
                reference=f"ITEM-{index + 1:03}",
            )
            for index in range(body.sample_size)
        ],
    )
    db.add(sample)
    db.flush()
    _log(
        db,
        engagement,
        user,
        "sample.created",
        "sample_set",
        sample.id,
        population=body.population,
        sample_size=body.sample_size,
    )
    db.commit()
    return _set_view(sample)


@router.patch(
    "/auditor/samples/{set_id}/items/{sample_item_id}",
    response_model=list[SampleSetView],
    response_model_by_alias=True,
)
def set_sample_result(
    set_id: str, sample_item_id: str, body: SampleResultBody, db: DB, user: CurrentUser
) -> list[SampleSetView]:
    if user.role != UserRole.AUDITOR:
        raise HTTPException(403, "Auditor access required")
    sample = db.get(SampleSet, set_id)
    # Same 404 for a missing set and one in an engagement this auditor is not assigned to.
    engagement = _get_engagement(db, user, sample.engagement_id) if sample else None
    if sample is None or engagement is None or sample.firm_id != engagement.firm_id:
        raise HTTPException(404, "Sample not found")
    item = db.scalar(
        select(SampleItem).where(
            SampleItem.id == sample_item_id,
            SampleItem.set_id == sample.id,
            SampleItem.firm_id == engagement.firm_id,
        )
    )
    if item is None:
        raise HTTPException(404, "Sample not found")
    previous = item.result
    item.result = body.result
    if body.note is not None:
        item.note = body.note
    item.updated_by_id = user.id
    item.updated_at = datetime.now(UTC)
    _log(
        db,
        engagement,
        user,
        "sample.result_set",
        "sample_item",
        item.id,
        set_id=sample.id,
        previous=previous,
        result=body.result,
    )
    db.commit()
    return _samples(db, engagement)
