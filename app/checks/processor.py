"""Document-check pipeline. Findings are internal drafts; client output stays document-level."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.checklist import ClientStatus
from app.config import Settings
from app.database.models import (
    AuditLog,
    ChecklistItemInstance,
    CheckResult,
    Document,
    Engagement,
    FindingDraft,
)
from app.egnyte_client import EgnyteClient

from .deterministic import contains_sar_indicator, run_deterministic_checks
from .providers import DocumentCheckProvider, LLMDocumentCheck, get_check_provider

CLIENT_REASONS = {
    "unreadable": "The file could not be read clearly. Please upload a clearer copy.",
    "wrong_period": "The file does not appear to cover the requested review period.",
    "wrong_document": "The uploaded file does not appear to be the requested document.",
    "missing_pages": "The file appears to be missing pages or supporting documents.",
}


class DownloadClient(Protocol):
    async def download_file(self, path: str) -> bytes: ...

    async def aclose(self) -> None: ...


class DocumentProcessor:
    def __init__(
        self,
        settings: Settings,
        *,
        provider: DocumentCheckProvider | None = None,
        client_factory: Callable[[Settings], DownloadClient] = EgnyteClient.from_settings,
    ) -> None:
        self.settings = settings
        self.provider = provider
        self.client_factory = client_factory

    async def process(self, db: Session, document_id: str) -> int:
        started = time.monotonic()
        document = db.scalar(
            select(Document)
            .where(Document.id == document_id)
            .options(
                selectinload(Document.item)
                .selectinload(ChecklistItemInstance.engagement)
                .selectinload(Engagement.firm)
            )
        )
        if not document:
            raise LookupError("document_not_found")
        item = document.item
        engagement = item.engagement
        if item.restricted:
            raise RuntimeError("restricted_item_was_queued")

        client = self.client_factory(self.settings)
        try:
            content = await client.download_file(document.egnyte_path)
        finally:
            await client.aclose()

        deterministic_started = time.monotonic()
        report = run_deterministic_checks(
            item=item,
            engagement=engagement,
            filename=document.original_name,
            content=content,
        )
        deterministic_ms = int((time.monotonic() - deterministic_started) * 1000)
        for check in report.checks:
            db.add(
                CheckResult(
                    firm_id=document.firm_id,
                    document_id=document.id,
                    check_type=check.check_type,
                    status=check.status,
                    client_reason=check.client_reason,
                    details=check.details,
                    duration_ms=deterministic_ms,
                )
            )

        if contains_sar_indicator(document.original_name, report.extracted):
            db.add(
                CheckResult(
                    firm_id=document.firm_id,
                    document_id=document.id,
                    check_type="restricted_content",
                    status="flagged_human_only",
                    details={"ai_called": False},
                    duration_ms=int((time.monotonic() - started) * 1000),
                )
            )
            item.status = ClientStatus.WITH_AUDITOR
            item.client_reason = "This file requires direct handling with the auditor."
            return self._finish(db, document, started, "restricted_human_only")

        if report.blocking_reason_code:
            item.status = (
                ClientStatus.ACTION_NEEDED_MORE
                if report.blocking_reason_code == "missing_pages"
                else ClientStatus.ACTION_NEEDED_REUPLOAD
            )
            item.client_reason = next(
                (check.client_reason for check in reversed(report.checks) if check.client_reason),
                CLIENT_REASONS.get(report.blocking_reason_code),
            )
            return self._finish(db, document, started, "deterministic_action_needed")

        if report.requires_manual_review:
            db.add(
                CheckResult(
                    firm_id=document.firm_id,
                    document_id=document.id,
                    check_type="text_extraction",
                    status="manual_review",
                    details={"ai_called": False},
                )
            )
            item.status = ClientStatus.WITH_AUDITOR
            item.client_reason = None
            return self._finish(db, document, started, "manual_review")

        provider = self.provider or get_check_provider(self.settings)
        llm_started = time.monotonic()
        try:
            llm_result = await provider.check(
                item_title=item.title,
                item_description=item.description,
                review_period_start=engagement.review_period_start.isoformat(),
                review_period_end=engagement.review_period_end.isoformat(),
                pages=report.extracted.pages,
            )
        finally:
            await provider.aclose()
        llm_ms = int((time.monotonic() - llm_started) * 1000)
        self._record_llm_result(db, document, item, llm_result, provider.name, llm_ms)
        return self._finish(db, document, started, "completed")

    def _record_llm_result(
        self,
        db: Session,
        document: Document,
        item: ChecklistItemInstance,
        result: LLMDocumentCheck,
        provider_name: str,
        duration_ms: int,
    ) -> None:
        citations = [
            citation.model_dump() for finding in result.findings for citation in finding.citations
        ]
        db.add(
            CheckResult(
                firm_id=document.firm_id,
                document_id=document.id,
                check_type="llm_document_check",
                status="completed",
                details={
                    "provider": provider_name,
                    "document_usable": result.document_usable,
                    "document_type_matches": result.document_type_matches,
                    "review_period_supported": result.review_period_supported,
                    "needs_more_documents": result.needs_more_documents,
                    "client_reason_code": result.client_reason_code,
                    "finding_count": len(result.findings),
                },
                citations=citations,
                duration_ms=duration_ms,
            )
        )
        for finding in result.findings:
            db.add(
                FindingDraft(
                    firm_id=document.firm_id,
                    engagement_id=item.engagement_id,
                    document_id=document.id,
                    title=finding.title,
                    body=finding.body,
                    severity=finding.severity,
                    citations=[citation.model_dump() for citation in finding.citations],
                )
            )

        reason_code = result.client_reason_code
        if not result.document_usable or not result.document_type_matches:
            item.status = (
                ClientStatus.ACTION_NEEDED_MORE
                if reason_code == "missing_pages"
                else ClientStatus.ACTION_NEEDED_REUPLOAD
            )
            safe_code = reason_code if reason_code != "none" else "wrong_document"
            item.client_reason = CLIENT_REASONS[safe_code]
        elif result.needs_more_documents:
            item.status = ClientStatus.ACTION_NEEDED_MORE
            safe_code = reason_code if reason_code != "none" else "missing_pages"
            item.client_reason = CLIENT_REASONS[safe_code]
        elif result.findings:
            item.status = ClientStatus.WITH_AUDITOR
            item.client_reason = None
        else:
            item.status = ClientStatus.ACCEPTED_FOR_TESTING
            item.client_reason = None

    def _finish(self, db: Session, document: Document, started: float, outcome: str) -> int:
        duration_ms = int((time.monotonic() - started) * 1000)
        db.add(
            AuditLog(
                firm_id=document.firm_id,
                action="document.checks_completed",
                entity_type="document",
                entity_id=document.id,
                details={"outcome": outcome, "duration_ms": duration_ms},
            )
        )
        db.flush()
        return duration_ms
