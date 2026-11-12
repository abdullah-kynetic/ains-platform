"""Request and output schemas. Output is fixed JSON; findings must cite document and page."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

DraftKind = Literal["finding", "document_flag", "client_request"]


class AnalyzeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # Scope: who is asking, for which firm and engagement. Checked on every call, never optional.
    firm_id: str = Field(min_length=1, max_length=64)
    engagement_id: str = Field(min_length=1, max_length=64)
    user_id: str = Field(min_length=1, max_length=64)
    item_id: str  # checklist request id, e.g. AML-BD-001
    document_id: str
    source: str  # must be "synthetic" during the trial
    tags: list[str] = Field(default_factory=list)  # document tags; SAR-flagged tags are blocked
    text: str  # synthetic document text (data, never instructions)
    prompt_version: str = "v1"  # "v1" document issues only; "v2" auditor analysis drafts
    # Used by prompt v2 only. Item text and rubric come from the checklist, never from uploads.
    item_title: str = Field(default="", max_length=300)
    item_text: str = Field(default="", max_length=4000)
    rubric: list[str] = Field(default_factory=list, max_length=20)
    page_count: int = Field(default=1, ge=1, le=10_000)  # cited pages must be within 1..page_count


class Finding(BaseModel):
    model_config = ConfigDict(extra="forbid")  # cannot smuggle status/finalize/sign fields

    document_id: str
    page: int = Field(ge=1)
    issue: str = Field(max_length=500)  # document issues only (v1) or the draft text (v2)
    kind: DraftKind = "finding"
    title: str = Field(default="", max_length=200)


class AnalyzeOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    findings: list[Finding] = Field(max_length=12)
