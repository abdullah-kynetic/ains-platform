"""Canonical request definitions; rubric interpretation belongs to Quinton."""

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, model_validator

CATALOG_PATH = Path(__file__).resolve().parents[2] / "data/checklist/aml_bd_v1.yaml"


class CatalogModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Rubric(CatalogModel):
    expected_evidence: list[str]
    timing: str | None
    alternatives: list[str]
    needs_human_decision: bool | None


class Conditions(CatalogModel):
    question: str
    when_yes: Literal["applicable"]
    when_no: Literal["representation_required", "proposed_not_applicable"]


class RequestDefinition(CatalogModel):
    id: str
    title: str
    client_description: str
    section: str
    conditions: Conditions | None
    allowed_evidence_types: list[str]
    restricted: bool
    stage: Literal["initial", "auditor_follow_up"]
    rubric: Rubric


class Section(CatalogModel):
    id: str
    title: str


class Catalog(CatalogModel):
    version: Literal["aml_bd_v1"]
    sections: list[Section]
    requests: list[RequestDefinition]

    @model_validator(mode="after")
    def complete_inventory(self) -> "Catalog":
        ids = [request.id for request in self.requests]
        expected = [f"AML-BD-{number:03}" for number in range(1, 35)]
        if len(ids) != len(set(ids)) or ids != expected:
            raise ValueError(
                "Checklist must contain exactly AML-BD-001 through AML-BD-034 in order"
            )
        sections = {section.id for section in self.sections}
        if len(sections) != len(self.sections):
            raise ValueError("Duplicate section IDs")
        for request in self.requests:
            if request.section not in sections:
                raise ValueError("Unknown section")
            if request.restricted and request.allowed_evidence_types:
                raise ValueError("Restricted requests cannot allow portal evidence")
        return self

    def get(self, request_id: str) -> RequestDefinition | None:
        return next((request for request in self.requests if request.id == request_id), None)


def load_catalog() -> Catalog:
    return Catalog.model_validate(yaml.safe_load(CATALOG_PATH.read_text(encoding="utf-8")))


def initialize_engagement(engagement) -> None:
    """Populate workflow instances; catalog fields remain authoritative when rendering."""
    from app.checklist import ClientStatus
    from app.database.models import ChecklistItemInstance

    if engagement.items:
        raise ValueError("Engagement already has request instances")
    catalog = load_catalog()
    # Preserve initialization provenance without replacing current catalog rendering.
    engagement.checklist_version = catalog.version
    engagement.checklist_snapshot = catalog.model_dump(mode="json")
    sections = {section.id: section.title for section in catalog.sections}
    for index, request in enumerate(catalog.requests):
        engagement.items.append(
            ChecklistItemInstance(
                firm_id=engagement.firm_id,
                item_key=request.id,
                position=index,
                title=request.title,
                description=request.client_description,
                section_key=request.section,
                section_title=sections[request.section],
                accepted_extensions=request.allowed_evidence_types,
                restricted=request.restricted,
                applicable=request.stage == "initial",
                is_conditional=request.conditions is not None,
                condition_question=request.conditions.question if request.conditions else None,
                status=(
                    ClientStatus.RESTRICTED_DO_NOT_UPLOAD
                    if request.restricted
                    else ClientStatus.REQUESTED
                ),
            )
        )
