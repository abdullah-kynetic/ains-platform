"""The approved inventory is complete, unique, and has no invented rubric."""

import pytest
from pydantic import ValidationError

from app.checklist.catalog import Catalog, load_catalog


def test_complete_canonical_inventory():
    catalog = load_catalog()
    assert [item.id for item in catalog.requests] == [
        f"AML-BD-{number:03}" for number in range(1, 35)
    ]
    for item in catalog.requests:
        assert item.title and item.client_description
        assert item.rubric.model_dump() == {
            "expected_evidence": [],
            "timing": None,
            "alternatives": [],
            "needs_human_decision": None,
        }
        assert item.allowed_evidence_types or item.restricted


@pytest.mark.parametrize("mutation", ["duplicate", "missing"])
def test_invalid_inventory_rejected(mutation):
    data = load_catalog().model_dump()
    if mutation == "duplicate":
        data["requests"][-1]["id"] = "AML-BD-001"
    else:
        data["requests"].pop()
    with pytest.raises(ValidationError, match="exactly AML-BD-001"):
        Catalog.model_validate(data)


def test_initialization_records_an_independent_catalog_snapshot():
    from datetime import date

    from app.checklist.catalog import initialize_engagement
    from app.database.models import Engagement, EngagementStatus

    engagement = Engagement(
        firm_id="synthetic-firm", status=EngagementStatus.DRAFT,
        review_period_start=date(2025, 1, 1), review_period_end=date(2025, 12, 31),
    )
    initialize_engagement(engagement)
    assert engagement.checklist_version == "aml_bd_v1"
    assert engagement.checklist_snapshot == load_catalog().model_dump(mode="json")
    engagement.items[0].title = "Synthetic instance change"
    assert engagement.checklist_snapshot["requests"][0]["title"] != engagement.items[0].title
    with pytest.raises(ValueError, match="already has"):
        initialize_engagement(engagement)
