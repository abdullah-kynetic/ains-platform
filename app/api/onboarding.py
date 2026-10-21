"""Auditor-owned draft engagements with frozen checklist definitions."""

from datetime import UTC, date, datetime
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import Field, model_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from app.checklist.catalog import ChecklistCatalog, load_catalog
from app.checklist.instances import initialize_checklist
from app.database.models import AuditLog, ChecklistItemInstance, Engagement, EngagementStatus, Firm

from .auditor import DB, APIModel, CurrentUser, _require_auditor

router = APIRouter(prefix="/auditor/engagements", tags=["onboarding"])


class NewEngagement(APIModel):
    firm_name: str = Field(min_length=1, max_length=255)
    firm_slug: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{1,98}[a-z0-9]$")
    review_period_start: date
    review_period_end: date
    due_date: date | None = None

    @model_validator(mode="after")
    def valid_period(self) -> "NewEngagement":
        if not self.firm_name.strip():
            raise ValueError("Firm name cannot be blank")
        if self.review_period_end < self.review_period_start:
            raise ValueError("Review period end must follow its start")
        return self


class DraftEngagement(APIModel):
    id: str
    firm_id: str
    firm_name: str
    status: EngagementStatus
    checklist_version: str | None
    item_count: int


class ChecklistReview(APIModel):
    engagement: DraftEngagement
    catalog: ChecklistCatalog
    follow_ups: list[dict[str, str | bool]]


def _view(engagement: Engagement) -> DraftEngagement:
    return DraftEngagement(
        id=engagement.id, firm_id=engagement.firm_id, firm_name=engagement.firm.name,
        status=engagement.status, checklist_version=engagement.checklist_version,
        item_count=len(engagement.items),
    )


@router.post("", response_model=DraftEngagement, status_code=201)
def create_engagement(payload: NewEngagement, user: CurrentUser, db: DB) -> DraftEngagement:
    _require_auditor(user)
    # Create a new tenant atomically. Existing tenants require a separate authorized
    # assignment flow; knowing another firm's slug never grants access to it.
    firm = Firm(name=payload.firm_name.strip(), slug=payload.firm_slug)
    engagement = Engagement(
        firm=firm, auditor_id=user.id, status=EngagementStatus.DRAFT,
        review_period_start=payload.review_period_start,
        review_period_end=payload.review_period_end, due_date=payload.due_date,
    )
    db.add(firm)
    db.add(engagement)
    try:
        db.flush()
        initialize_checklist(engagement, load_catalog())
        db.add(AuditLog(
            firm_id=firm.id, actor_id=user.id, action="engagement.draft_created",
            entity_type="engagement", entity_id=engagement.id,
            details={"checklist_version": engagement.checklist_version},
        ))
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Firm identifier is unavailable") from None
    return _view(engagement)


@router.get("", response_model=list[DraftEngagement])
def list_engagements(user: CurrentUser, db: DB) -> list[DraftEngagement]:
    _require_auditor(user)
    engagements = db.scalars(select(Engagement).where(
        Engagement.auditor_id == user.id,
    ).options(selectinload(Engagement.firm), selectinload(Engagement.items)))
    return [_view(engagement) for engagement in engagements]


class PublishChecklist(APIModel):
    confirm_checklist_reviewed: Literal[True]
    review_notes: str = Field(min_length=10, max_length=5000)


def _assigned_engagement(engagement_id: str, user: CurrentUser, db: DB) -> Engagement:
    _require_auditor(user)
    engagement = db.scalar(select(Engagement).where(
        Engagement.id == engagement_id, Engagement.auditor_id == user.id,
    ).options(selectinload(Engagement.firm), selectinload(Engagement.items)))
    if not engagement:
        raise HTTPException(status_code=404, detail="Engagement not found")
    return engagement


@router.get("/{engagement_id}/checklist", response_model=ChecklistReview)
def review_checklist(engagement_id: str, user: CurrentUser, db: DB) -> ChecklistReview:
    engagement = _assigned_engagement(engagement_id, user, db)
    if not engagement.checklist_snapshot:
        raise HTTPException(status_code=404, detail="No checklist snapshot for this engagement")
    catalog = ChecklistCatalog.model_validate(engagement.checklist_snapshot)
    follow_up_keys = {item.id for item in catalog.items if item.intake_stage == "auditor_follow_up"}
    return ChecklistReview(
        engagement=_view(engagement), catalog=catalog,
        follow_ups=[{"id": item.id, "title": item.title, "released": item.applicable}
                    for item in engagement.items if item.item_key in follow_up_keys],
    )


@router.post("/{engagement_id}/publish", response_model=DraftEngagement)
def publish_checklist(
    engagement_id: str, payload: PublishChecklist, user: CurrentUser, db: DB,
) -> DraftEngagement:
    engagement = _assigned_engagement(engagement_id, user, db)
    if engagement.status != EngagementStatus.DRAFT or not engagement.checklist_snapshot:
        raise HTTPException(status_code=409, detail="Only a catalog-backed draft can be published")
    catalog = ChecklistCatalog.model_validate(engagement.checklist_snapshot)
    if len(engagement.items) != len(catalog.items):
        raise HTTPException(status_code=409, detail="Engagement checklist is incomplete")
    # Approval belongs to this engagement; the source catalog stays pending review.
    engagement.status = EngagementStatus.COLLECTING
    db.add(AuditLog(
        firm_id=engagement.firm_id, actor_id=user.id, action="checklist.approved_and_published",
        entity_type="engagement", entity_id=engagement.id,
        details={"checklist_version": catalog.version, "review_notes": payload.review_notes,
                 "approved_at": datetime.now(UTC).isoformat()},
    ))
    db.commit()
    return _view(engagement)


class ReleaseFollowUp(APIModel):
    selection_notes: str = Field(min_length=10, max_length=5000)


@router.post("/{engagement_id}/items/{item_id}/release")
def release_follow_up(
    engagement_id: str, item_id: str, payload: ReleaseFollowUp, user: CurrentUser, db: DB,
) -> dict[str, str]:
    engagement = _assigned_engagement(engagement_id, user, db)
    if engagement.status != EngagementStatus.COLLECTING:
        raise HTTPException(status_code=409, detail="Engagement is not collecting documents")
    item = db.scalar(select(ChecklistItemInstance).where(
        ChecklistItemInstance.id == item_id,
        ChecklistItemInstance.engagement_id == engagement.id,
        ChecklistItemInstance.firm_id == engagement.firm_id,
    ))
    definitions = (engagement.checklist_snapshot or {}).get("items", [])
    definition = next((entry for entry in definitions if item and entry["id"] == item.item_key), {})
    if not item or definition.get("intake_stage") != "auditor_follow_up":
        raise HTTPException(status_code=404, detail="Follow-up request not found")
    if item.applicable:
        raise HTTPException(status_code=409, detail="Follow-up is already released")
    item.applicable = True
    db.add(AuditLog(
        firm_id=engagement.firm_id, actor_id=user.id, action="checklist.follow_up_released",
        entity_type="checklist_item_instance", entity_id=item.id,
        details={"selection_notes": payload.selection_notes},
    ))
    db.commit()
    return {"status": "released"}
