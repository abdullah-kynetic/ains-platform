from datetime import date
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.checklist import ClientStatus
from app.checklist.catalog import ChecklistCatalog, load_catalog
from app.checklist.instances import initialize_checklist
from app.database.models import Engagement, EngagementStatus


def test_catalog_preserves_all_source_requests_and_alternatives() -> None:
    catalog = load_catalog()
    source = Path(catalog.source).read_text()
    assert len(catalog.items) == 34
    assert len(catalog.sections) == 6
    assert all(item.description in source for item in catalog.items)
    assert [item.source_position for item in catalog.items] == list(range(1, 35))
    assert catalog.items[8].intake_stage == "auditor_follow_up"
    assert all(catalog.items[i - 1].restricted for i in (17, 25))
    assert all(catalog.items[i - 1].negative_answer_instruction for i in (12, 16, 22, 24))


@pytest.mark.parametrize("mutation", ["missing", "unrestricted", "duplicate"])
def test_invalid_catalog_is_rejected(mutation: str) -> None:
    data = load_catalog().model_dump()
    if mutation == "missing":
        data["items"].pop()
    elif mutation == "unrestricted":
        data["items"][16]["restricted"] = False
    else:
        data["items"][1]["id"] = data["items"][0]["id"]
    with pytest.raises(ValidationError):
        ChecklistCatalog.model_validate(data)


def test_engagement_snapshot_is_independent_and_cannot_be_reinitialized() -> None:
    engagement = Engagement(
        firm_id="synthetic-firm", status=EngagementStatus.DRAFT,
        review_period_start=date(2025, 1, 1), review_period_end=date(2025, 12, 31),
    )
    catalog = load_catalog()
    initialize_checklist(engagement, catalog)
    assert len(engagement.items) == 34
    assert engagement.items[16].status == ClientStatus.RESTRICTED_DO_NOT_UPLOAD
    assert not engagement.items[8].applicable
    catalog.items[0].title = "Changed catalog"
    assert engagement.items[0].title != catalog.items[0].title
    assert engagement.checklist_snapshot["items"][0]["title"] != catalog.items[0].title
    with pytest.raises(ValueError, match="already initialized"):
        initialize_checklist(engagement, catalog)
