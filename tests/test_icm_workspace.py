"""Walk test for the ICM contract files: every link and input path must resolve."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FILES = [ROOT / "CONTEXT.md", ROOT / "docs" / "ICM-PLAN.md", *ROOT.glob("*/CONTEXT.md")]
LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
TICK = re.compile(r"`([^`\s]+)`")
PENDING: set[str] = set()  # paths that exist only after another open PR merges


def _inputs(text: str) -> list[str]:
    section = re.search(r"^## Inputs\n(.*?)(?=^## )", text, re.M | re.S)
    if not section:
        return []
    out: list[str] = []
    for line in section.group(1).splitlines():
        if line.startswith("- Reference"):
            out += TICK.findall(line.split(":", 1)[1])[:1]
    return out


def test_contract_files_exist() -> None:
    assert len(FILES) >= 9
    for name in ("app", "ai_adapter", "audit_engine", "web", "tests", "scripts", "data", "docs"):
        assert (ROOT / name / "CONTEXT.md").is_file(), name


def test_links_and_reference_inputs_resolve() -> None:
    missing: list[str] = []
    for f in FILES:
        text = f.read_text()
        targets = [t.split("#")[0] for t in LINK.findall(text) if not t.startswith(("http", "#"))]
        for t in targets:
            if t and t not in PENDING and not (f.parent / t).exists():
                missing.append(f"{f.relative_to(ROOT)} -> {t}")
        if f.name == "CONTEXT.md" and f.parent != ROOT:
            for t in _inputs(text):
                if "/" in t or "." in t:
                    if t not in PENDING and not (f.parent / t).exists():
                        missing.append(f"{f.relative_to(ROOT)} input {t}")
    assert not missing, missing


def test_contracts_stay_small_and_have_a_check() -> None:
    for f in FILES:
        if f.name == "CONTEXT.md" and f.parent != ROOT:
            text = f.read_text()
            assert len(text.splitlines()) <= 80, f
            assert "## Check" in text and "## Inputs" in text, f
