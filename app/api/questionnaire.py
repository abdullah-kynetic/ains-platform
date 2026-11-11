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
from app.checklist.applicability import record_na_change
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
                answer=False
                if item.status == ClientStatus.NOT_APPLICABLE
                else item.applicability_answer,
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
    # Decision (2026-11-10): the reasoned N/A flow is the only way to mark a request N/A. The
    # client gives a reason and the auditor approves or rejects. The questionnaire marks none.
    if any(not answer.applies for answer in payload.answers):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "The questionnaire cannot mark a request as not applicable. Use "
                "'Does not apply' on the document checklist and give a reason."
            ),
        )
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
        representation = answer.representation if not answer.applies else None
        if (
            (item.status == ClientStatus.NOT_APPLICABLE) == (not answer.applies)
            and item.applicability_answer == answer.applies
            and item.representation == representation
        ):
            continue
        before = {"answer": item.applicability_answer, "representation": item.representation}
        record_na_change(db, item, user, not answer.applies)
        item.assessment = None
        item.applicability_answer = answer.applies
        item.representation = answer.representation if not answer.applies else None
        if answer.applies:
            item.applicability_decision = None
            item.na_approved_by_id = None
            item.applicable = True
            item.na_review_state = None
            item.na_requested_at = None
            item.status = (
                ClientStatus.RESTRICTED_DO_NOT_UPLOAD if item.restricted else ClientStatus.REQUESTED
            )
        else:
            item.na_requested_at = now
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
