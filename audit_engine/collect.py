"""Evidence requests and collection from a synthetic firm folder."""

import json
import re
from pathlib import Path

from app.checklist.catalog import Catalog, load_catalog
from audit_engine.models import (
    Collection,
    EvidenceFile,
    EvidenceGap,
    EvidenceRequest,
)

FIRMS_ROOT = Path(__file__).resolve().parents[1] / "data" / "synthetic" / "firms"
_PERIOD = re.compile(r"^Period:\s*(\d{4})\s*$", re.MULTILINE)


def collect_firm(
    slug: str,
    declared_na: set[str] | None = None,
    catalog: Catalog | None = None,
    root: Path = FIRMS_ROOT,
) -> Collection:
    """Inventory a firm folder. `declared_na` models the client marking items N/A.

    Restricted (SAR-related) items are never requested or read.
    """
    catalog = catalog or load_catalog()
    declared_na = declared_na or set()
    folder = root / slug
    meta = json.loads((root / "index.json").read_text(encoding="utf-8"))[slug]
    requests: list[EvidenceRequest] = []
    files: list[EvidenceFile] = []
    gaps: list[EvidenceGap] = []
    for request in catalog.requests:
        base = dict(
            item_id=request.id,
            title=request.title,
            description=request.client_description,
            allowed_evidence_types=request.allowed_evidence_types,
        )
        if request.restricted:
            requests.append(EvidenceRequest(**base, state="restricted"))
            continue
        if request.id in declared_na:
            requests.append(EvidenceRequest(**base, state="not_applicable"))
            continue
        matches = sorted(p for p in folder.glob(f"{request.id}.*") if p.is_file())
        if not matches:
            requests.append(EvidenceRequest(**base, state="requested"))
            gaps.append(EvidenceGap(item_id=request.id, reason="missing"))
            continue
        requests.append(EvidenceRequest(**base, state="collected"))
        for path in matches:
            files.append(
                EvidenceFile(
                    item_id=request.id,
                    document_id=path.name,
                    text=path.read_text(encoding="utf-8"),
                )
            )
    first = next((m.group(1) for f in files if (m := _PERIOD.search(f.text))), "")
    return Collection(
        firm=meta["name"],
        period=_most_common_period(files) or first,
        requests=requests,
        files=files,
        gaps=gaps,
    )


def _most_common_period(files: list[EvidenceFile]) -> str:
    counts: dict[str, int] = {}
    for f in files:
        match = _PERIOD.search(f.text)
        if match:
            counts[match.group(1)] = counts.get(match.group(1), 0) + 1
    return max(counts, key=counts.__getitem__) if counts else ""
