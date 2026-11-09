"""Typed records. Every observation is a draft: only a human auditor approves anything."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class EngineModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class TestStep(EngineModel):
    __test__ = False  # not a pytest class

    step_id: str  # e.g. AML-BD-003.S2
    item_id: str
    kind: Literal["existence", "period", "completeness", "currency", "consistency", "integrity"]
    procedure: str
    # Rubric wording belongs to Quentin. Steps stay unapproved until a human sets this.
    approved_by_auditor: bool = False


class EvidenceRequest(EngineModel):
    item_id: str
    title: str
    description: str
    allowed_evidence_types: list[str]
    state: Literal["requested", "collected", "not_applicable", "restricted"]


class EvidenceFile(EngineModel):
    item_id: str
    document_id: str  # file name, unique within one firm
    text: str


class EvidenceGap(EngineModel):
    item_id: str
    reason: Literal["missing"]


class Observation(EngineModel):
    """A possible document issue. A draft until an auditor accepts or rejects it."""

    item_id: str
    document_id: str
    page: int = Field(ge=1)
    code: str  # shared defect taxonomy, e.g. D-UNSIGNED
    issue: str = Field(max_length=500)
    source: Literal["rules", "model"] = "rules"
    status: Literal["draft"] = "draft"


class Collection(EngineModel):
    firm: str
    period: str
    requests: list[EvidenceRequest]
    files: list[EvidenceFile]
    gaps: list[EvidenceGap]
