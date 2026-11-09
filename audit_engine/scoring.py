"""Score engine output against a synthetic firm's answer key (planted defects)."""

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from audit_engine.models import Collection, Observation


class Score(BaseModel):
    model_config = ConfigDict(extra="forbid")

    firm: str
    expected: int
    found: int
    false_positives: int
    missed: list[str]
    unexpected: list[str]
    recall: float
    precision: float


def load_answer_key(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def expected_items(key: dict) -> dict[str, str]:
    """item id -> defect id, for planted defects and planted missing items."""
    return {
        i["item_id"]: i["defect_id"]
        for i in key["items"]
        if i["expected_status"] in {"defect", "missing"}
    }


def declared_na(key: dict) -> set[str]:
    """The client's N/A declarations are workflow input, not an answer."""
    return {i["item_id"] for i in key["items"] if i["expected_status"] == "not_applicable"}


def score(key: dict, collection: Collection, observations: list[Observation]) -> Score:
    """Item-level scoring. A planted defect is found if the engine raises the same code
    for that item, or if it is a missing item and the collection shows the gap."""
    expected = expected_items(key)
    raised = {(o.item_id, o.code) for o in observations}
    raised |= {(g.item_id, "D-MISSING") for g in collection.gaps}
    # D-NO-INDEPENDENT-TEST is a missing item with its own code.
    hits = {
        i
        for i, code in expected.items()
        if (i, code) in raised or (code == "D-NO-INDEPENDENT-TEST" and (i, "D-MISSING") in raised)
    }
    expected_pairs = {(i, c) for i, c in expected.items()}
    expected_pairs |= {
        (i, "D-MISSING") for i, c in expected.items() if c == "D-NO-INDEPENDENT-TEST"
    }
    unexpected = sorted(f"{i}:{c}" for i, c in raised - expected_pairs)
    missed = sorted(set(expected) - hits)
    found = len(hits)
    total = len(expected)
    return Score(
        firm=key["firm"],
        expected=total,
        found=found,
        false_positives=len(unexpected),
        missed=missed,
        unexpected=unexpected,
        recall=found / total if total else 1.0,
        precision=found / (found + len(unexpected)) if (found + len(unexpected)) else 1.0,
    )
