"""Reversible human applicability decisions; never audit criteria."""
from app.checklist import ClientStatus
from app.database.models import ChecklistItemInstance, NAReviewState

FIELDS = ("status", "applicable", "applicability_decision", "assessment", "na_review_state",
          "na_approved_by_id", "follow_up", "client_reason")


def set_na(item: ChecklistItemInstance, actor_id: str) -> None:
    if item.status != ClientStatus.NOT_APPLICABLE:
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
        "status": ClientStatus.RESTRICTED_DO_NOT_UPLOAD if item.restricted else (
            ClientStatus.WITH_AUDITOR if item.documents else ClientStatus.REQUESTED),
        "applicable": True, "applicability_decision": None, "assessment": None,
        "na_review_state": None, "na_approved_by_id": None,
    }
    for key, value in previous.items():
        if key == "status":
            value = ClientStatus(value)
        elif key == "na_review_state" and value:
            value = NAReviewState(value)
        setattr(item, key, value)
    item.na_previous_state = None
