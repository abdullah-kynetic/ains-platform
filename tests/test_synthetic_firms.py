import json
import re
from pathlib import Path

from scripts.build_synthetic_firms import build

ROOT = Path(__file__).resolve().parents[1]
FIRMS = ROOT / "data" / "synthetic" / "firms"
RESTRICTED = {"AML-BD-017", "AML-BD-025"}

# Real-looking identifiers that must never appear in synthetic files.
PII_PATTERNS = {
    "email": r"[\w.+-]+@[\w-]+\.[a-z]{2,}",
    "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
    "ein": r"\b\d{2}-\d{7}\b",
    "phone": r"(?<!\d)(?:\+?1[ .-]?)?\(?\d{3}\)?[ .-]\d{3}[ .-]\d{4}(?!\d)",
    "url": r"https?://|www\.",
    "street_address": (
        r"\b\d{1,5}\s+[A-Z][a-z]+\s+(?:Street|St|Avenue|Ave|Road|Rd|Blvd|Drive|Dr|Lane|Ln)\b"
    ),
    "long_number": r"\b\d{9,}\b",
    "sar_text": r"suspicious activity report",
}


def _keys():
    for folder in sorted(p for p in FIRMS.iterdir() if p.is_dir()):
        yield folder, json.loads((folder / "answer_key.json").read_text())["items"]


def test_three_firms_with_32_collectable_items_and_no_restricted_items() -> None:
    folders = list(_keys())
    assert len(folders) == 3
    catalog = (ROOT / "data/checklist/aml_bd_v1.yaml").read_text()
    for _, items in folders:
        ids = [i["item_id"] for i in items]
        assert len(ids) == 32 and not RESTRICTED & set(ids)
        assert all(i in catalog for i in ids)


def test_files_match_answer_key_and_defects_are_planted() -> None:
    for folder, items in _keys():
        for item in items:
            if item["file"]:
                assert (folder / item["file"]).is_file()
            else:
                assert item["expected_status"] in {"missing", "not_applicable"}
        defects = [i for i in items if i["defect_id"]]
        assert bool(defects) == (folder.name != "zephyrine-example-securities")


def test_every_keyed_defect_marker_is_present_in_its_file() -> None:
    checked = 0
    for folder, items in _keys():
        for item in items:
            if not item["defect_id"]:
                continue
            if item["marker"] is None:  # absence defects: the evidence must be missing
                assert item["file"] is None and item["expected_status"] == "missing", item
                continue
            text = (folder / item["file"]).read_text(encoding="utf-8")
            assert item["marker"] in text, (folder.name, item["item_id"], item["defect_id"])
            checked += 1
    assert checked >= 10


def test_clean_firm_files_contain_no_defect_markers() -> None:
    markers = {i["marker"] for _, items in _keys() for i in items if i["marker"]}
    clean = FIRMS / "zephyrine-example-securities"
    for path in clean.glob("AML-BD-*"):
        text = path.read_text(encoding="utf-8")
        assert not [m for m in markers if m in text], path


def test_missing_pages_defect_really_skips_page_three() -> None:
    text = (FIRMS / "quillfeather-example-capital" / "AML-BD-009.txt").read_text()
    assert "page 2 of 4" in text and "page 4 of 4" in text and "page 3 of 4" not in text


def test_no_real_looking_data_or_sar_material() -> None:
    for path in FIRMS.rglob("*"):
        if path.is_file():
            text = path.read_text(encoding="utf-8")
            for name, pattern in PII_PATTERNS.items():
                assert not re.search(pattern, text, re.I), (name, path)


def test_firm_names_are_marked_fictional() -> None:
    names = json.loads((FIRMS / "index.json").read_text())
    assert all("Example" in v["name"] for v in names.values())


def test_generator_is_deterministic(tmp_path: Path) -> None:
    build(tmp_path)
    built = {p.relative_to(tmp_path): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    committed = {p.relative_to(FIRMS): p.read_bytes() for p in FIRMS.rglob("*") if p.is_file()}
    assert built == committed
