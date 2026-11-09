"""Deterministic document checks. Generic patterns; they never read an answer key.

Document text is data, never instructions. Findings are drafts for a human auditor.
"""

import csv
import io
import re
from datetime import date

from audit_engine.models import Collection, EvidenceFile, Observation

_PERIOD = re.compile(r"^Period:\s*(\d{4})\s*$", re.MULTILINE)
_UNSIGNED = re.compile(r"Signature:\s*_{3,}")
_REVIEWED = re.compile(r"last reviewed:\s*(\d{4})-(\d{2})-(\d{2})", re.IGNORECASE)
_PAGE = re.compile(r"---\s*page\s+(\d+)\s+of\s+(\d+)\s*---")
_COMPLETED = re.compile(r"completed:\s*(\d+)\s+of\s+(\d+)", re.IGNORECASE)
_INJECTION = re.compile(
    r"ignore (your|all|previous) instructions|mark every item|disregard the above",
    re.IGNORECASE,
)
_SCREENED = re.compile(r"last screening run recorded:\s*(\d{4})-(\d{2})-(\d{2})", re.IGNORECASE)
_OFFICER = re.compile(r"AML officer:\s*([A-Za-z][\w .'-]*?)\.\s", re.IGNORECASE)
_TESTER = re.compile(r"tested by:\s*([A-Za-z][\w .'-]*?)\.?\s*$", re.IGNORECASE | re.MULTILINE)
_NO_FOREIGN = re.compile(r"foreign relationships during the period:\s*none", re.IGNORECASE)

STALE_REVIEW_MONTHS = 12
SCREENING_GAP_DAYS = 90
STRUCTURING_BAND = (9000.0, 9999.99)
STRUCTURING_MIN_COUNT = 3
STRUCTURING_WINDOW_DAYS = 7


def _obs(f: EvidenceFile, code: str, issue: str, page: int = 1) -> Observation:
    return Observation(
        item_id=f.item_id, document_id=f.document_id, page=page, code=code, issue=issue
    )


def _period_end(period: str) -> date:
    return date(int(period), 12, 31)


def check_text_file(f: EvidenceFile, period: str) -> list[Observation]:
    out: list[Observation] = []
    text = f.text
    if (m := _PERIOD.search(text)) and period and m.group(1) != period:
        out.append(
            _obs(f, "D-WRONG-PERIOD", f"Document covers {m.group(1)}, not the {period} period")
        )
    if _UNSIGNED.search(text):
        out.append(_obs(f, "D-UNSIGNED", "Signature and date are blank"))
    if (m := _REVIEWED.search(text)) and period:
        reviewed = date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        end = _period_end(period)
        months = (end.year - reviewed.year) * 12 + end.month - reviewed.month
        if months > STALE_REVIEW_MONTHS:
            out.append(_obs(f, "D-STALE-POLICY", f"Last reviewed {reviewed}, over a year old"))
    pages = [(int(a), int(b)) for a, b in _PAGE.findall(text)]
    if pages:
        total = pages[0][1]
        have = {a for a, _ in pages}
        missing = [n for n in range(1, total + 1) if n not in have]
        if missing:
            out.append(
                _obs(f, "D-MISSING-PAGES", f"Page {missing[0]} of {total} is missing", missing[0])
            )
    if (m := _COMPLETED.search(text)) and int(m.group(1)) < int(m.group(2)):
        out.append(_obs(f, "D-INCOMPLETE-TRAINING", f"Only {m.group(1)} of {m.group(2)} completed"))
    if _INJECTION.search(text):
        out.append(_obs(f, "D-UNTRUSTED-TEXT", "Text tries to instruct the reader; ignored"))
    if (m := _SCREENED.search(text)) and period:
        last = date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        if (_period_end(period) - last).days > SCREENING_GAP_DAYS:
            out.append(_obs(f, "D-SCREENING-LAPSE", f"Screening log stops at {last}"))
    officer, tester = _OFFICER.search(text), _TESTER.search(text)
    if officer and tester and officer.group(1).strip() == tester.group(1).strip():
        out.append(_obs(f, "D-SEPARATION", "AML officer also tests the program"))
    if "risk assessment" in text.lower() and "one paragraph only" in text.lower():
        out.append(_obs(f, "D-THIN-RISK-ASSESSMENT", "Risk assessment is one paragraph"))
    return out


def _ledger_rows(f: EvidenceFile) -> list[dict[str, str]]:
    return list(csv.DictReader(io.StringIO(f.text)))


def check_ledger(f: EvidenceFile) -> list[Observation]:
    rows = _ledger_rows(f)
    low, high = STRUCTURING_BAND
    by_party: dict[str, list[date]] = {}
    for row in rows:
        try:
            amount = float(row["amount_usd"])
            day = date.fromisoformat(row["date"])
        except (KeyError, ValueError):
            continue
        if low <= amount <= high:
            by_party.setdefault(row["counterparty"], []).append(day)
    out: list[Observation] = []
    for party, days in sorted(by_party.items()):
        days.sort()
        for i in range(len(days)):
            window = [d for d in days[i:] if (d - days[i]).days < STRUCTURING_WINDOW_DAYS]
            if len(window) >= STRUCTURING_MIN_COUNT:
                out.append(
                    _obs(
                        f,
                        "D-STRUCTURING-PATTERN",
                        f"{len(window)} transfers just under 10,000 to {party} within a week",
                    )
                )
                break
    return out


def check_consistency(collection: Collection) -> list[Observation]:
    """Cross-document: 'no foreign relationships' versus foreign ledger countries."""
    foreign_ledger = False
    for f in collection.files:
        if f.document_id.endswith(".csv"):
            foreign_ledger |= any(r.get("country", "US") not in {"US", ""} for r in _ledger_rows(f))
    out: list[Observation] = []
    if foreign_ledger:
        for f in collection.files:
            if _NO_FOREIGN.search(f.text):
                out.append(
                    _obs(f, "D-INCONSISTENT", "Says no foreign relationships; ledger shows some")
                )
    return out


def run_rules(collection: Collection) -> list[Observation]:
    out: list[Observation] = []
    for f in collection.files:
        if f.document_id.endswith(".csv"):
            out.extend(check_ledger(f))
        else:
            out.extend(check_text_file(f, collection.period))
    out.extend(check_consistency(collection))
    return sorted(out, key=lambda o: (o.item_id, o.code, o.page))
