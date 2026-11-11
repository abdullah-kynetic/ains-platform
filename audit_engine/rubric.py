"""Load the DRAFT rubric. It is prompt context for drafting only, never an approved criterion."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

RUBRIC_PATH = Path(__file__).with_name("rubric_draft.yaml")


@lru_cache
def _load() -> dict:
    data = yaml.safe_load(RUBRIC_PATH.read_text())
    if "DRAFT" not in str(data.get("status", "")):
        raise ValueError("rubric file must stay marked DRAFT until Quentin approves it")
    return data["items"]


def rubric_for(item_key: str) -> list[str]:
    entry = _load().get(item_key)
    return list(entry["criteria"]) if entry else []


def rubric_items() -> set[str]:
    return set(_load())
