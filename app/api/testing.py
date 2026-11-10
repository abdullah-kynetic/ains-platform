"""Checklist test conclusions (L2-6b): the auditor's own pass / partial / fail / na per request.

A conclusion is a human entry recorded as typed; nothing here derives or suggests one, and the
client never receives it (these routes are auditor-only and the client views do not carry it).
Engagement scope is the assigned-auditor filter; items are matched by ``firm_id`` and engagement.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.checklist.catalog import load_catalog
from app.database.models import AuditLog, ChecklistItemInstance, Engagement, User, UserRole
from app.workflow import item_state, open_issue_counts

from .engagements import DB, CurrentUser
from .questionnaire import _get_engagement

router = APIRouter(tags=["testing"])

Conclusion = Literal["pass", "partial", "fail", "na"]


class ChecklistTestView(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    request_id: str
    title: str
    section: str
    restricted: bool
    conclusion: Conclusion | None
    updated_at: datetime | None


class ConclusionBody(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="forbid")
    conclusion: Conclusion | None


def _auditor_engagement(db: Session, user: User, engagement_id: str) -> Engagement:
    if user.role != UserRole.AUDITOR:
        raise HTTPException(403, "Auditor access required")
    return _get_engagement(db, user, engagement_id)


def _tests(db: Session, engagement: Engagement) -> list[ChecklistTestView]:
    order = {request.id: index for index, request in enumerate(load_catalog().requests)}
    sections = {request.id: request.section for request in load_catalog().requests}
    open_issues = open_issue_counts(db, engagement)
    items = db.scalars(
        select(ChecklistItemInstance).where(
            ChecklistItemInstance.engagement_id == engagement.id,
            ChecklistItemInstance.firm_id == engagement.firm_id,
        )
    ).all()
    rows = [item for item in items if item.item_key in order]

    def is_na(item: ChecklistItemInstance) -> bool:
        return item.conclusion == "na" or item_state(item, open_issues.get(item.id, 0)) == "na"

    # N/A rows sort last; otherwise catalog order. Original request ids never change.
    rows.sort(key=lambda item: (is_na(item), order[item.item_key]))
    return [
        ChecklistTestView(
            request_id=item.item_key,
            title=item.title,
            section=sections[item.item_key],
            restricted=bool(item.restricted),
            conclusion=item.conclusion,  # type: ignore[arg-type]
            updated_at=item.conclusion_updated_at,
        )
        for item in rows
    ]


@router.get(
    "/auditor/engagements/{engagement_id}/checklist-tests",
    response_model=list[ChecklistTestView],
    response_model_by_alias=True,
)
def list_checklist_tests(engagement_id: str, db: DB, user: CurrentUser) -> list[ChecklistTestView]:
    return _tests(db, _auditor_engagement(db, user, engagement_id))


@router.patch(
    "/auditor/engagements/{engagement_id}/checklist-tests/{request_id}",
    response_model=list[ChecklistTestView],
    response_model_by_alias=True,
)
def set_conclusion(
    engagement_id: str, request_id: str, body: ConclusionBody, db: DB, user: CurrentUser
) -> list[ChecklistTestView]:
    engagement = _auditor_engagement(db, user, engagement_id)
    item = db.scalar(
        select(ChecklistItemInstance).where(
            ChecklistItemInstance.engagement_id == engagement.id,
            ChecklistItemInstance.firm_id == engagement.firm_id,
            ChecklistItemInstance.item_key == request_id,
        )
    )
    if item is None:
        raise HTTPException(404, "Request not found")
    previous = item.conclusion
    item.conclusion = body.conclusion
    item.conclusion_updated_at = datetime.now(UTC)
    item.conclusion_updated_by_id = user.id
    db.add(
        AuditLog(
            firm_id=engagement.firm_id,
            actor_id=user.id,
            action="checklist.conclusion_set",
            entity_type="checklist_item",
            entity_id=item.id,
            details={"request_id": request_id, "from": previous, "to": body.conclusion},
        )
    )
    db.commit()
    return _tests(db, engagement)
