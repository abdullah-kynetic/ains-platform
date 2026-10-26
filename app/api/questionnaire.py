"""Firm questionnaire and auditor review of not-applicable answers."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.checklist import ClientStatus
from app.checklist.applicability import set_na, unset_na
from app.checklist.catalog import load_catalog
from app.database.models import (
    AuditLog,
    ChecklistItemInstance,
    Engagement,
    NAReviewState,
    User,
    UserRole,
)
from app.database.session import get_db

from .engagements import visible_engagements

router = APIRouter(tags=["questionnaire"])
DB = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


class APIModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)


class QuestionView(APIModel):
    item_id: str
    section_title: str
    question: str
    answer: bool | None
    na_review_state: NAReviewState | None
    when_no: str
    representation: str | None


class QuestionnaireView(APIModel):
    engagement_id: str
    questions: list[QuestionView]


class QuestionAnswer(APIModel):
    item_id: str
    applies: bool
    representation: Literal["no_activity", "not_applicable"] | None = None


class QuestionnaireAnswers(APIModel):
    answers: list[QuestionAnswer] = Field(min_length=1, max_length=200)


class NAReviewDecision(APIModel):
    decision: Literal["approve", "reject"]


def _get_engagement(db: Session, user: User, engagement_id: str) -> Engagement:
    engagement = db.scalar(visible_engagements(user).where(Engagement.id == engagement_id))
    if not engagement:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Engagement not found")
    return engagement


def _questionnaire(db: Session, engagement: Engagement) -> QuestionnaireView:
    catalog = load_catalog()
    section_titles = {section.id: section.title for section in catalog.sections}
    items = db.scalars(
        select(ChecklistItemInstance)
        .where(
            ChecklistItemInstance.engagement_id == engagement.id,
            ChecklistItemInstance.firm_id == engagement.firm_id,
        )
        .order_by(ChecklistItemInstance.position)
    )
    return QuestionnaireView(
        engagement_id=engagement.id,
        questions=[
            QuestionView(
                item_id=item.id,
                section_title=section_titles[definition.section],
                question=definition.conditions.question,
                answer=item.applicability_answer,
                na_review_state=item.na_review_state,
                when_no=definition.conditions.when_no,
                representation=item.representation,
            )
            for item in items
            if (definition := catalog.get(item.item_key)) and definition.conditions
        ],
    )


@router.get(
    "/engagements/{engagement_id}/questionnaire",
    response_model=QuestionnaireView,
    response_model_by_alias=True,
)
def read_questionnaire(engagement_id: str, user: CurrentUser, db: DB) -> QuestionnaireView:
    return _questionnaire(db, _get_engagement(db, user, engagement_id))


@router.post(
    "/engagements/{engagement_id}/questionnaire/answers",
    response_model=QuestionnaireView,
    response_model_by_alias=True,
)
def answer_questionnaire(
    engagement_id: str,
    payload: QuestionnaireAnswers,
    user: CurrentUser,
    db: DB,
) -> QuestionnaireView:
    if user.role != UserRole.CLIENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only firm users can answer the firm questionnaire",
        )
    engagement = _get_engagement(db, user, engagement_id)
    answer_ids = {answer.item_id for answer in payload.answers}
    if len(answer_ids) != len(payload.answers):
        raise HTTPException(status_code=422, detail="Each questionnaire item may be answered once")
    items = {
        item.id: item
        for item in db.scalars(
            select(ChecklistItemInstance).where(
                ChecklistItemInstance.id.in_(answer_ids),
                ChecklistItemInstance.engagement_id == engagement.id,
                ChecklistItemInstance.firm_id == engagement.firm_id,
            )
        )
    }
    if items.keys() != answer_ids:
        raise HTTPException(status_code=404, detail="Questionnaire item not found")
    catalog = load_catalog()
    if any(
        not (definition := catalog.get(item.item_key)) or not definition.conditions
        for item in items.values()
    ):
        raise HTTPException(status_code=404, detail="Questionnaire item not found")

    now = datetime.now(UTC)
    for answer in payload.answers:
        definition = catalog.get(items[answer.item_id].item_key)
        if (
            not answer.applies
            and definition.conditions.when_no == "representation_required"
            and not answer.representation
        ):
            raise HTTPException(422, "Confirm a representation for each no-activity answer")
    for answer in payload.answers:
        item = items[answer.item_id]
        if item.status == ClientStatus.NOT_APPLICABLE:
            raise HTTPException(409, "Ask your auditor to reopen this N/A request")
        representation = answer.representation if not answer.applies else None
        if item.applicability_answer == answer.applies and item.representation == representation:
            continue
        before = {"answer": item.applicability_answer, "representation": item.representation}
        item.applicability_decision = None
        item.assessment = None
        item.applicability_answer = answer.applies
        item.representation = answer.representation if not answer.applies else None
        item.na_approved_by_id = None
        if answer.applies:
            item.applicable = True
            item.na_review_state = None
            item.na_requested_at = None
            item.status = (
                ClientStatus.RESTRICTED_DO_NOT_UPLOAD if item.restricted else ClientStatus.REQUESTED
            )
        else:
            item.applicable = False
            item.na_review_state = NAReviewState.PENDING
            item.na_requested_at = now
            item.status = ClientStatus.WITH_AUDITOR
        db.add(
            AuditLog(
                firm_id=engagement.firm_id,
                actor_id=user.id,
                action="questionnaire.answered",
                entity_type="checklist_item_instance",
                entity_id=item.id,
                details={
                    "before": before,
                    "after": {"answer": answer.applies, "representation": item.representation},
                },
            )
        )
    db.commit()
    return _questionnaire(db, engagement)


@router.post(
    "/engagements/{engagement_id}/questionnaire/items/{item_id}/na-review",
    response_model=QuestionView,
    response_model_by_alias=True,
)
def review_not_applicable(
    engagement_id: str,
    item_id: str,
    payload: NAReviewDecision,
    user: CurrentUser,
    db: DB,
) -> QuestionView:
    if user.role != UserRole.AUDITOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the assigned auditor can review N/A answers",
        )
    engagement = _get_engagement(db, user, engagement_id)
    item = db.scalar(
        select(ChecklistItemInstance).where(
            ChecklistItemInstance.id == item_id,
            ChecklistItemInstance.engagement_id == engagement.id,
            ChecklistItemInstance.firm_id == engagement.firm_id,
            ChecklistItemInstance.na_review_state == NAReviewState.PENDING,
        )
    )
    if not item:
        raise HTTPException(status_code=404, detail="Pending N/A answer not found")
    catalog = load_catalog()
    definition = catalog.get(item.item_key)
    if not definition or not definition.conditions:
        raise HTTPException(status_code=404, detail="Pending N/A answer not found")

    before = {"applicable": item.applicable, "na_review_state": item.na_review_state}
    if payload.decision == "approve":
        set_na(item, user.id)
    item.na_approved_by_id = user.id
    item.applicability_decision = (
        "not_applicable" if payload.decision == "approve" else "applicable"
    )
    item.assessment = None
    if payload.decision == "approve":
        item.na_review_state = NAReviewState.APPROVED
        item.applicable = False
    else:
        unset_na(item)
        item.na_review_state = NAReviewState.REJECTED
        item.applicable = True
        item.status = (
            ClientStatus.RESTRICTED_DO_NOT_UPLOAD if item.restricted else ClientStatus.REQUESTED
        )
        item.client_reason = "The auditor confirmed that this requested item applies."
    db.add(
        AuditLog(
            firm_id=engagement.firm_id,
            actor_id=user.id,
            action=(
                "questionnaire.na_approved"
                if payload.decision == "approve"
                else "questionnaire.na_rejected"
            ),
            entity_type="checklist_item_instance",
            entity_id=item.id,
            details={
                "before": before,
                "after": {"applicable": item.applicable, "na_review_state": item.na_review_state},
            },
        )
    )
    db.commit()
    return QuestionView(
        item_id=item.id,
        section_title=next(
            section.title for section in catalog.sections if section.id == definition.section
        ),
        question=definition.conditions.question,
        answer=item.applicability_answer,
        na_review_state=item.na_review_state,
        when_no=definition.conditions.when_no,
        representation=item.representation,
    )
