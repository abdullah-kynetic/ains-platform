import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIRMS = ROOT / "data" / "synthetic" / "firms"
RESTRICTED = {"AML-BD-017", "AML-BD-025"}


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
        assert bool(defects) == (folder.name != "northgate-securities")


def test_no_real_looking_data_or_sar_material() -> None:
    pattern = re.compile(
        r"(@[a-z0-9-]+\.[a-z]{2,}|\b\d{3}-\d{2}-\d{4}\b|suspicious activity report)", re.I
    )
    for path in FIRMS.rglob("*"):
        if path.is_file():
            assert not pattern.search(path.read_text(encoding="utf-8")), path


def test_generator_is_deterministic() -> None:
    from scripts.build_synthetic_firms import build

    before = {p: p.read_bytes() for p in FIRMS.rglob("*") if p.is_file()}
    build()
    assert before == {p: p.read_bytes() for p in FIRMS.rglob("*") if p.is_file()}
