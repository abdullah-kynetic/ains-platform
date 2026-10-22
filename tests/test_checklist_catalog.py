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
