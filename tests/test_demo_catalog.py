"""The generated demo data must retain the authoritative request definitions."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from app.checklist.catalog import load_catalog

_WEB_DEPS = Path("web/node_modules/yaml").exists() and shutil.which("node") is not None


@pytest.mark.skipif(not _WEB_DEPS, reason="web dependencies (npm ci in web/) not installed")
def test_demo_catalog_matches_authoritative_version() -> None:
    subprocess.run(["node", "scripts/generate-catalog.mjs"], cwd="web", check=True)
    demo = json.loads(Path("web/.generated/catalog.json").read_text())
    assert demo == load_catalog().model_dump(mode="json")
