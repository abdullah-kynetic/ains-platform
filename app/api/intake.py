"""Neutral client intake feedback and declarations, never audit findings."""

from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from app.checklist import ClientStatus
from app.checklist.applicability import unset_na
from app.checklist.catalog import load_catalog
from app.database.models import AuditLog, ChecklistItemInstance, Document, NAReviewState, UserRole

from .engagements import DB, CurrentUser
from .questionnaire import _get_engagement

router = APIRouter(tags=["intake"])
FEEDBACK = {
    "unreadable": "Please replace this file with a readable copy.",
    "wrong_document": "Please replace this file with the requested document.",
    "wrong_period": "Please provide a file covering the engagement review period.",
    "missing_pages": "Please provide the missing pages or a complete copy.",
}


class Representation(BaseModel):
    kind: Literal["no_activity", "not_applicable"]
    confirmed: Literal[True]


class Feedback(BaseModel):
    code: Literal["unreadable", "wrong_document", "wrong_period", "missing_pages", "usable"]
    document_id: str


def intake_item(db, user, engagement_id, item_id):
    engagement = _get_engagement(db, user, engagement_id)
    item = db.scalar(
        select(ChecklistItemInstance).where(
            ChecklistItemInstance.id == item_id,
            ChecklistItemInstance.engagement_id == engagement.id,
            ChecklistItemInstance.firm_id == engagement.firm_id,
        )
    )
    if not item or not load_catalog().get(item.item_key):
        raise HTTPException(404, "Request not found")
    return engagement, item


@router.post("/engagements/{engagement_id}/items/{item_id}/representations")
def represent(engagement_id: str, item_id: str, payload: Representation, user: CurrentUser, db: DB):
    if user.role != UserRole.CLIENT:
        raise HTTPException(403, "Only firm users can make representations")
    engagement, item = intake_item(db, user, engagement_id, item_id)
    definition = load_catalog().get(item.item_key)
    if item.status == ClientStatus.NOT_APPLICABLE:
        raise HTTPException(409, "Ask your auditor to reopen this N/A request")
    if definition.restricted or not definition.conditions:
        raise HTTPException(409, "This request requires direct auditor handling")
    before = {"representation": item.representation, "na_review_state": item.na_review_state}
    item.representation = payload.kind
    item.applicability_decision = None
    item.assessment = None
    item.applicability_answer = False
    item.applicable = False
    item.na_review_state = NAReviewState.PENDING
    item.na_approved_by_id = None
    item.status = ClientStatus.WITH_AUDITOR
    db.add(
        AuditLog(
            firm_id=engagement.firm_id,
            actor_id=user.id,
            action="representation.submitted",
            entity_type="checklist_item_instance",
            entity_id=item.id,
            details={
                "before": before,
                "after": {"representation": item.representation, "na_review_state": "pending"},
            },
        )
    )
    db.commit()
    return {"status": "pending_auditor_review"}


@router.post("/auditor/engagements/{engagement_id}/items/{item_id}/follow-up")
def follow_up(engagement_id: str, item_id: str, user: CurrentUser, db: DB):
    if user.role != UserRole.AUDITOR:
        raise HTTPException(403, "Auditor access required")
    engagement, item = intake_item(db, user, engagement_id, item_id)
    definition = load_catalog().get(item.item_key)
    if definition.restricted:
        raise HTTPException(409, "Restricted requests cannot be released for upload")
    before = {"applicable": item.applicable, "follow_up": item.follow_up}
    unset_na(item)
    item.applicable = True
    item.follow_up = True
    item.assessment = None
    item.applicability_decision = None
    if item.na_review_state == NAReviewState.PENDING:
        item.na_review_state = NAReviewState.REJECTED
    item.status = ClientStatus.REQUESTED
    item.client_reason = "Your auditor has requested this additional document."
    db.add(
        AuditLog(
            firm_id=engagement.firm_id,
            actor_id=user.id,
            action="request.follow_up",
            entity_type="checklist_item_instance",
            entity_id=item.id,
            details={"before": before, "after": {"applicable": True, "follow_up": True}},
        )
    )
    db.commit()
    return {"status": "requested"}


@router.post("/auditor/engagements/{engagement_id}/items/{item_id}/feedback")
def feedback(engagement_id: str, item_id: str, payload: Feedback, user: CurrentUser, db: DB):
    if user.role != UserRole.AUDITOR:
        raise HTTPException(403, "Auditor access required")
    engagement, item = intake_item(db, user, engagement_id, item_id)
    document = db.scalar(
        select(Document).where(
            Document.id == payload.document_id,
            Document.item_instance_id == item.id,
            Document.firm_id == engagement.firm_id,
        )
    )
    if not document:
        raise HTTPException(404, "Document not found")
    before = {"feedback_code": document.feedback_code, "status": item.status}
    document.feedback_code = None if payload.code == "usable" else payload.code
    item.assessment = None
    item.status = (
        ClientStatus.WITH_AUDITOR
        if payload.code == "usable"
        else (
            ClientStatus.ACTION_NEEDED_MORE
            if payload.code == "missing_pages"
            else ClientStatus.ACTION_NEEDED_REUPLOAD
        )
    )
    item.client_reason = FEEDBACK.get(payload.code)
    db.add(
        AuditLog(
            firm_id=engagement.firm_id,
            actor_id=user.id,
            action="document.feedback",
            entity_type="checklist_item_instance",
            entity_id=item.id,
            details={
                "document_id": document.id,
                "before": before,
                "after": {"feedback_code": payload.code, "status": item.status},
            },
        )
    )
    db.commit()
    return {"status": item.status, "reason": item.client_reason}
