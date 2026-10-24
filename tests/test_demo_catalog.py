"""The generated demo data must retain the authoritative request definitions."""
import json
import subprocess
from pathlib import Path

from app.checklist.catalog import load_catalog


def test_demo_catalog_matches_authoritative_version() -> None:
    subprocess.run(["node", "scripts/generate-catalog.mjs"], cwd="web", check=True)
    demo = json.loads(Path("web/.generated/catalog.json").read_text())
    assert demo == load_catalog().model_dump(mode="json")
