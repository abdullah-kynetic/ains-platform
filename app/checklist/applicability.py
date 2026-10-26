"""Reversible human applicability decisions; never audit criteria."""

from sqlalchemy.orm import Session

from app.checklist import ClientStatus
from app.database.models import AuditLog, ChecklistItemInstance, NAReviewState, User

FIELDS = (
    "status",
    "applicable",
    "applicability_decision",
    "assessment",
    "na_review_state",
    "na_approved_by_id",
    "applicability_answer",
    "representation",
    "follow_up",
    "client_reason",
)


def set_na(item: ChecklistItemInstance, actor_id: str) -> None:
    if item.status == ClientStatus.NOT_APPLICABLE:
        return
    item.na_previous_state = {key: getattr(item, key) for key in FIELDS}
    item.status = ClientStatus.NOT_APPLICABLE
    item.applicable = False
    item.applicability_decision = "not_applicable"
    item.assessment = None
    item.na_review_state = NAReviewState.APPROVED
    item.na_approved_by_id = actor_id
    item.follow_up = False
    item.client_reason = None


def unset_na(item: ChecklistItemInstance) -> None:
    if item.status != ClientStatus.NOT_APPLICABLE:
        return
    previous = item.na_previous_state or {
        "status": ClientStatus.RESTRICTED_DO_NOT_UPLOAD
        if item.restricted
        else (ClientStatus.WITH_AUDITOR if item.documents else ClientStatus.REQUESTED),
        "applicable": True,
        "applicability_decision": None,
        "assessment": None,
        "na_review_state": None,
        "na_approved_by_id": None,
    }
    for key, value in previous.items():
        if key == "status":
            value = ClientStatus(value)
        elif key == "na_review_state" and value:
            value = NAReviewState(value)
        setattr(item, key, value)
    item.na_previous_state = None


def record_na_change(db: Session, item: ChecklistItemInstance, actor: User, value: bool) -> None:
    """Persist a reversible declaration and its actor in the business transaction."""
    db.refresh(item, with_for_update=True)
    before = item.status
    if value:
        set_na(item, actor.id)
    else:
        unset_na(item)
    db.add(
        AuditLog(
            firm_id=item.firm_id,
            actor_id=actor.id,
            action="request.na_set" if value else "request.na_unset",
            entity_type="checklist_item_instance",
            entity_id=item.id,
            details={"before": before, "after": item.status, "actor_role": actor.role.value},
        )
    )
