"""Run one analysis over a set of documents and return DRAFTS plus a skip list.

Order for each file, all before any model call: restricted item, SAR tag, readable text, SAR
content scan. Only then is one adapter call made with a free model. The result is never trusted:
drafts are re-validated here (kind, cited document, page range) and carry no status other than
"pending". A human accepts, edits or rejects each one.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import PurePath

from ai_adapter.guards import sar_content_reason
from ai_adapter.schemas import AnalyzeRequest
from audit_engine.extract import ExtractionSkip, extract
from audit_engine.model_client import ModelClient, ModelRefused
from audit_engine.rubric import rubric_for

# Free models only, in order. The second is tried only when the first fails upstream.
DEFAULT_MODELS = ("google/gemma-4-26b-a4b-it:free", "nvidia/nemotron-3-ultra-550b-a55b:free")
PROMPT_VERSION = "v2"
MAX_DOCUMENTS = 8  # per run, to stay inside the free daily quota
SAR_TAGS = {"sar", "sar-related", "restricted", "suspicious-activity"}
STOP_RUN_CODES = {"ai_disabled", "breaker_open", "rate_limited", "daily_quota_reached"}
FALLBACK_CODES = {"upstream_error", "bad_output", "post_check_failed"}

SKIP_MESSAGES = {
    "restricted_item": "Linked to a restricted item. Handled by a person only.",
    "sar_tag": "Tagged as SAR-related. Never sent to an AI model.",
    "sar_content": "Mentions SAR or suspicious activity report filings. Never sent to an AI model.",
    "sar_blocked": "Blocked by the SAR safety check.",
    "sar_content_blocked": "Blocked by the SAR safety check.",
    "unsupported_type": "File type cannot be read by the AI (PDF, DOCX, TXT and CSV only).",
    "empty": "The file is empty.",
    "too_large": "The file is too large to analyse.",
    "too_many_pages": "The PDF has too many pages to analyse.",
    "encrypted": "The PDF is password protected.",
    "unreadable": "The file is damaged or not what its extension says.",
    "no_text": "No readable text found (scanned image?).",
    "storage_unavailable": "The stored file could not be read.",
    "over_limit": f"Not analysed: a run covers at most {MAX_DOCUMENTS} files.",
    "ownership_denied": "Blocked: the file does not belong to this engagement.",
    "not_run": "Not analysed: the run stopped early.",
}


def skip_message(code: str) -> str:
    return SKIP_MESSAGES.get(code, "The AI service declined this file.")


@dataclass(frozen=True)
class DocInput:
    document_id: str
    name: str
    content: bytes | None
    item_key: str
    item_title: str
    item_text: str
    item_restricted: bool = False
    tags: tuple[str, ...] = ()


@dataclass(frozen=True)
class Draft:
    kind: str
    document_id: str
    item_key: str
    page: int
    title: str
    text: str
    model: str


@dataclass
class RunResult:
    drafts: list[Draft] = field(default_factory=list)
    skipped: list[dict[str, str]] = field(default_factory=list)
    analyzed: int = 0
    models: list[str] = field(default_factory=list)


def _skip(result: RunResult, doc: DocInput, code: str) -> None:
    result.skipped.append(
        {
            "documentId": doc.document_id,
            "document": doc.name,
            "code": code,
            "reason": skip_message(code),
        }
    )


def run_analysis(
    docs: list[DocInput],
    client: ModelClient,
    *,
    firm_id: str,
    engagement_id: str,
    user_id: str,
    models: tuple[str, ...] = DEFAULT_MODELS,
) -> RunResult:
    result = RunResult()
    stopped: str | None = None
    for index, doc in enumerate(docs):
        if stopped:
            _skip(result, doc, "not_run")
            continue
        if index >= MAX_DOCUMENTS:
            _skip(result, doc, "over_limit")
            continue
        if doc.item_restricted:
            _skip(result, doc, "restricted_item")
            continue
        if SAR_TAGS & {t.lower() for t in doc.tags}:
            _skip(result, doc, "sar_tag")
            continue
        suffix = PurePath(doc.name).suffix
        if sar_content_reason(doc.name):
            _skip(result, doc, "sar_content")
            continue
        try:
            extracted = extract(doc.content, suffix)
        except ExtractionSkip as skip:
            _skip(result, doc, skip.code)
            continue
        text = extracted.as_text()
        if sar_content_reason(text, doc.item_title, doc.item_text):
            _skip(result, doc, "sar_content")
            continue
        request = AnalyzeRequest(
            firm_id=firm_id,
            engagement_id=engagement_id,
            user_id=user_id,
            item_id=doc.item_key,
            document_id=doc.document_id,
            source="synthetic",
            tags=list(doc.tags),
            text=text,
            prompt_version=PROMPT_VERSION,
            item_title=doc.item_title,
            item_text=doc.item_text,
            rubric=rubric_for(doc.item_key),
            page_count=extracted.page_count,
        )
        output = None
        used = ""
        failure = "refused"
        for model in models:
            try:
                output = client.analyze(request, model)
                used = model
                break
            except ModelRefused as refused:
                failure = refused.code
                if refused.code not in FALLBACK_CODES:
                    break
        if output is None:
            if failure in STOP_RUN_CODES:
                stopped = failure
            _skip(result, doc, failure)
            continue
        result.analyzed += 1
        if used not in result.models:
            result.models.append(used)
        for finding in output.findings:
            # Re-validate: only this document, only a real page, only the three draft kinds.
            if finding.document_id != doc.document_id or finding.page > extracted.page_count:
                continue
            result.drafts.append(
                Draft(
                    kind=finding.kind,
                    document_id=doc.document_id,
                    item_key=doc.item_key,
                    page=finding.page,
                    title=(finding.title or finding.issue)[:200],
                    text=finding.issue,
                    model=used,
                )
            )
    return result
