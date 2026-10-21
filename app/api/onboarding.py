"""Auditor-owned draft engagements with frozen checklist definitions."""

from datetime import date

from fastapi import APIRouter, HTTPException
from pydantic import Field, model_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from app.checklist.catalog import load_catalog
from app.checklist.instances import initialize_checklist
from app.database.models import AuditLog, Engagement, EngagementStatus, Firm

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
