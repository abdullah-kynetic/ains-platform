"""Checklist-driven test steps. Generic procedures only; no audit criteria are invented.

Each step is derived from a catalog request. Criteria in the catalog rubric stay empty until
Quentin approves them, so every step ships with approved_by_auditor=False.
"""

from app.checklist.catalog import Catalog, load_catalog
from audit_engine.models import TestStep

_GENERIC = (
    ("existence", "Confirm the evidence for '{title}' was provided, or that N/A was declared."),
    ("period", "Confirm the evidence covers the engagement period."),
    ("completeness", "Confirm the evidence is complete (all pages, all required parts)."),
    ("currency", "Confirm dates, reviews and signatures are current and present."),
    ("consistency", "Confirm the evidence agrees with the firm's other evidence."),
)


def build_steps(catalog: Catalog | None = None) -> list[TestStep]:
    catalog = catalog or load_catalog()
    steps: list[TestStep] = []
    for request in catalog.requests:
        if request.restricted:
            continue  # SAR-related items get no engine steps; humans handle them
        for number, (kind, text) in enumerate(_GENERIC, start=1):
            steps.append(
                TestStep(
                    step_id=f"{request.id}.S{number}",
                    item_id=request.id,
                    kind=kind,  # type: ignore[arg-type]
                    procedure=text.format(title=request.title),
                )
            )
    return steps
