"""Validated, versioned request catalog. Source interpretation remains auditor reviewed."""

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

CATALOG_ROOT = Path(__file__).resolve().parents[2] / "data" / "checklist"


class CatalogModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Section(CatalogModel):
    id: str
    title: str


class Request(CatalogModel):
    id: str = Field(pattern=r"^AML-BD-\d{3}$")
    source_position: int = Field(ge=1)
    source_title: str
    title: str
    description: str
    section: str
    accepted_document_types: list[str] = Field(min_length=1)
    format_rule: str
    review_period_rule: str
    applicability: Literal["always", "conditional"]
    condition_question: str | None
    negative_answer_requires_representation: bool
    negative_answer_instruction: str | None
    intake_stage: Literal["initial", "auditor_follow_up"]
    restricted: bool
    requires_signature: bool
    min_pages: int = Field(ge=1)
    review_notes: list[str]

    @model_validator(mode="after")
    def validate_condition(self) -> "Request":
        if (self.applicability == "conditional") != bool(self.condition_question):
            raise ValueError("Conditional requests require a deciding question")
        if self.negative_answer_requires_representation and not self.negative_answer_instruction:
            raise ValueError("Representation alternatives require instructions")
        return self


class ChecklistCatalog(CatalogModel):
    version: str
    approval_status: Literal["pending_quinton_review", "approved"]
    source: str
    sections: list[Section]
    items: list[Request]

    @model_validator(mode="after")
    def validate_inventory(self) -> "ChecklistCatalog":
        ids = [item.id for item in self.items]
        sections = [section.id for section in self.sections]
        if len(set(ids)) != len(ids) or len(set(sections)) != len(sections):
            raise ValueError("Catalog identifiers must be unique")
        if any(item.section not in sections for item in self.items):
            raise ValueError("Unknown section")
        if self.version == "aml_bd_v1":
            if ids != [f"AML-BD-{number:03}" for number in range(1, 35)]:
                raise ValueError("All 34 source requests must remain in source order")
            if not all(self.items[index - 1].restricted for index in (17, 25)):
                raise ValueError("SAR requests must remain restricted")
        return self


def load_catalog(version: str = "aml_bd_v1") -> ChecklistCatalog:
    if version != "aml_bd_v1":
        raise ValueError("Unknown checklist version")
    return ChecklistCatalog.model_validate(
        yaml.safe_load((CATALOG_ROOT / f"{version}.yaml").read_text(encoding="utf-8"))
    )
