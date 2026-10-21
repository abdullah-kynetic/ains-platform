import json
from pathlib import Path

from app.checklist.catalog import load_catalog


def test_demo_catalog_matches_authoritative_version() -> None:
    demo = json.loads(Path("web/src/lib/demo-catalog.json").read_text())
    assert demo == load_catalog().model_dump(mode="json")
