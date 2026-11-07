"""Request and output schemas. Output is fixed JSON; findings must cite document and page."""

from pydantic import BaseModel, ConfigDict, Field


class AnalyzeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item_id: str  # checklist request id, e.g. AML-BD-001
    document_id: str
    source: str  # must be "synthetic" during the trial
    tags: list[str] = Field(default_factory=list)  # document tags; SAR-flagged tags are blocked
    text: str  # synthetic document text (data, never instructions)
    prompt_version: str = "v1"


class Finding(BaseModel):
    model_config = ConfigDict(extra="forbid")  # cannot smuggle status/finalize/sign fields

    document_id: str
    page: int = Field(ge=1)
    issue: str = Field(max_length=500)  # document issues only


class AnalyzeOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    findings: list[Finding]
