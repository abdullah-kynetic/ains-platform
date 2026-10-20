"""Checklist items and the statuses clients see in the portal."""

from enum import StrEnum


class ClientStatus(StrEnum):
    """Client-facing status of a checklist item.

    Labels never imply an audit result: ACCEPTED_FOR_TESTING means the document
    is usable for testing, not that the firm passed.
    """

    REQUESTED = "requested"
    CHECKING = "checking"
    ACTION_NEEDED_REUPLOAD = "action_needed_reupload"
    ACTION_NEEDED_MORE = "action_needed_more"
    WITH_AUDITOR = "with_auditor"
    ACCEPTED_FOR_TESTING = "accepted_for_testing"
    # SAR-related items: never uploaded to the portal; auditor contacts the client.
    RESTRICTED_DO_NOT_UPLOAD = "restricted_do_not_upload"


__all__ = ["ClientStatus"]
