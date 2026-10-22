"""Assigned-auditor manual workflow. No inference or client-facing conclusions."""

from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.checklist import ClientStatus
from app.checklist.catalog import initialize_engagement, load_catalog
from app.database.models import (
    AuditLog,
    ChecklistItemInstance,
    Engagement,
    FindingDraft,
    NAReviewState,
    User,
    UserRole,
)

from .engagements import DB, CurrentUser, visible_engagements
from .intake import intake_item
from .questionnaire import _get_engagement

router = APIRouter(prefix="/auditor", tags=["manual review"])


def require_auditor(user):
    if user.role != UserRole.AUDITOR:
        raise HTTPException(403, "Auditor access required")


class ManualDecision(BaseModel):
    applicability: Literal["applicable", "not_applicable"]
    assessment: Literal["supported", "partial", "conflicting", "unable_to_determine"] | None
    notes: str = Field(max_length=5000)

    @model_validator(mode="after")
    def consistent(self):
        if self.applicability == "not_applicable" and self.assessment is not None:
            raise ValueError("A non-applicable request must not carry an evidence assessment")
        if self.applicability == "applicable" and self.assessment is None:
            raise ValueError("Choose an evidence assessment for an applicable request")
        if (
            self.applicability == "not_applicable" or self.assessment != "supported"
        ) and not self.notes.strip():
            raise ValueError("Document the reason for this decision in internal notes")
        return self


def readiness(engagement):
    catalog = load_catalog()
    instances = {item.item_key: item for item in engagement.items}
    blockers = []
    reviewed = 0
    for definition in catalog.requests:
        item = instances.get(definition.id)
        if not item:
            blockers.append(f"{definition.id}: workflow instance missing")
            continue
        if not item.applicability_decision:
            blockers.append(f"{definition.id}: applicability undecided")
        elif item.applicability_decision == "applicable" and not item.assessment:
            blockers.append(f"{definition.id}: assessment undecided")
        else:
            reviewed += 1
        if item.na_review_state == NAReviewState.PENDING:
            blockers.append(f"{definition.id}: client representation awaits review")
        if item.status.value == "checking":
            blockers.append(f"{definition.id}: storage receipt verification pending")
        if item.applicability_decision == "applicable" and item.status.value.startswith(
            "action_needed"
        ):
            blockers.append(f"{definition.id}: replacement or additional document requested")
    return {
        "ready": not blockers,
        "reviewed": reviewed,
        "total": 34,
        "blockers": blockers,
        "meaning": "Ready for human report drafting, not a clean opinion or signed report.",
    }


@router.get("/engagements")
def dashboard(user: CurrentUser, db: DB):
    require_auditor(user)
    engagements = db.scalars(
        visible_engagements(user).options(
            selectinload(Engagement.firm), selectinload(Engagement.items)
        )
    ).all()
    return [
        {
            "id": entry.id,
            "firmName": entry.firm.name,
            "status": entry.status,
            "readiness": readiness(entry),
        }
        for entry in engagements
    ]


@router.post("/engagements/{engagement_id}/initialize")
def initialize(engagement_id: str, user: CurrentUser, db: DB):
    require_auditor(user)
    engagement = _get_engagement(db, user, engagement_id)
    if engagement.items:
        raise HTTPException(409, "Existing request instances require explicit migration")
    initialize_engagement(engagement)
    db.add(
        AuditLog(
            firm_id=engagement.firm_id,
            actor_id=user.id,
            action="engagement.initialized",
            entity_type="engagement",
            entity_id=engagement.id,
            details={"before": {"requests": 0}, "after": {"requests": 34}},
        )
    )
    db.commit()
    return {"requests": 34}


@router.get("/engagements/{engagement_id}/workspace")
def workspace(engagement_id: str, user: CurrentUser, db: DB):
    require_auditor(user)
    engagement = _get_engagement(db, user, engagement_id)
    catalog = load_catalog()
    items = db.scalars(
        select(ChecklistItemInstance)
        .where(
            ChecklistItemInstance.engagement_id == engagement.id,
            ChecklistItemInstance.firm_id == engagement.firm_id,
        )
        .options(selectinload(ChecklistItemInstance.documents))
    ).all()
    instances = {item.item_key: item for item in items}
    requests = []
    for definition in catalog.requests:
        item = instances.get(definition.id)
        if item is None:
            continue
        requests.append(
            {
                "id": item.id,
                "requestId": definition.id,
                "title": definition.title,
                "restricted": definition.restricted,
                "stage": definition.stage,
                "applicable": item.applicable,
                "followUp": item.follow_up,
                "naReviewState": item.na_review_state,
                "representation": item.representation,
                "applicability": item.applicability_decision,
                "assessment": item.assessment,
                "notes": item.internal_notes,
                "documents": [
                    {
                        "id": doc.id,
                        "name": doc.original_name,
                        "sha256": doc.sha256,
                        "version": doc.version,
                        "uploadedAt": doc.created_at,
                        "feedbackCode": doc.feedback_code,
                    }
                    for doc in item.documents
                ],
            }
        )
    entity_ids = [
        engagement.id,
        *[item.id for item in items],
        *[doc.id for item in items for doc in item.documents],
    ]
    entity_ids.extend(
        db.scalars(
            select(FindingDraft.id).where(
                FindingDraft.engagement_id == engagement.id,
                FindingDraft.firm_id == engagement.firm_id,
            )
        )
    )
    events = db.execute(
        select(AuditLog, User.name)
        .outerjoin(User, User.id == AuditLog.actor_id)
        .where(AuditLog.firm_id == engagement.firm_id, AuditLog.entity_id.in_(entity_ids))
        .order_by(AuditLog.created_at, AuditLog.id)
    ).all()
    return {
        "id": engagement.id,
        "firmName": engagement.firm.name,
        "requests": requests,
        "readiness": readiness(engagement),
        "history": [
            {
                "id": event.id,
                "actorId": event.actor_id,
                "actor": name or "Storage worker",
                "action": event.action,
                "entityId": event.entity_id,
                "at": event.created_at,
                "details": event.details,
            }
            for event, name in events
        ],
    }


@router.patch("/engagements/{engagement_id}/items/{item_id}/decision")
def decide(engagement_id: str, item_id: str, payload: ManualDecision, user: CurrentUser, db: DB):
    require_auditor(user)
    engagement, item = intake_item(db, user, engagement_id, item_id)
    before = {
        "applicability": item.applicability_decision,
        "assessment": item.assessment,
        "notes": item.internal_notes,
    }
    item.applicability_decision = payload.applicability
    item.assessment = payload.assessment
    item.internal_notes = payload.notes
    item.applicable = payload.applicability == "applicable"
    if item.na_review_state is not None:
        item.na_review_state = NAReviewState.REJECTED if item.applicable else NAReviewState.APPROVED
        item.na_approved_by_id = user.id
        if item.applicable:
            definition = load_catalog().get(item.item_key)
            item.status = (
                ClientStatus.RESTRICTED_DO_NOT_UPLOAD
                if definition.restricted
                else ClientStatus.WITH_AUDITOR
                if item.documents
                else ClientStatus.REQUESTED
            )
            item.client_reason = "The auditor confirmed that this requested item applies."
    db.add(
        AuditLog(
            firm_id=engagement.firm_id,
            actor_id=user.id,
            action="request.manual_decision",
            entity_type="checklist_item_instance",
            entity_id=item.id,
            details={"before": before, "after": payload.model_dump()},
        )
    )
    db.commit()
    return {"status": "saved", "readiness": readiness(engagement)}
