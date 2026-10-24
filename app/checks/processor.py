"""Storage receipt verification only. Audit decisions belong to the auditor."""

from __future__ import annotations

import hashlib
import time
from collections.abc import Callable
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.checklist import ClientStatus
from app.config import Settings
from app.database.models import AuditLog, CheckResult, Document
from app.egnyte_client import EgnyteClient


class DownloadClient(Protocol):
    async def download_file(self, path: str) -> bytes: ...
    async def aclose(self) -> None: ...


class DocumentProcessor:
    def __init__(
        self, settings: Settings, *,
        client_factory: Callable[[Settings], DownloadClient] | None = None,
    ) -> None:
        self.settings = settings
        from app.storage.s3 import S3Storage

        self.client_factory = client_factory or (
            S3Storage if settings.storage_backend == "s3" else EgnyteClient.from_settings
        )

    async def process(self, db: Session, document_id: str) -> int:
        started = time.monotonic()
        document = db.scalar(select(Document).where(Document.id == document_id)
                             .options(selectinload(Document.item)))
        if not document:
            raise LookupError("document_not_found")
        if document.item.restricted:
            raise RuntimeError("restricted_item_was_queued")
        if document.egnyte_path.startswith("s3://"):
            prefix = f"s3://{self.settings.s3_bucket}/firms/{document.firm_id}/"
            if not document.egnyte_path.startswith(prefix):
                raise ValueError("cross_firm_storage_receipt")
        client = self.client_factory(self.settings)
        try:
            content = await client.download_file(document.egnyte_path)
        finally:
            await client.aclose()
        if hashlib.sha256(content).hexdigest() != document.sha256:
            raise ValueError("stored_document_fingerprint_mismatch")
        duration_ms = int((time.monotonic() - started) * 1000)
        db.add(CheckResult(
            firm_id=document.firm_id, document_id=document.id,
            check_type="storage_receipt", status="received",
            details={"sha256_verified": True}, duration_ms=duration_ms,
        ))
        # Receipt verification must not erase a later auditor replacement request
        # or a pending client representation.
        if document.item.status == ClientStatus.CHECKING:
            document.item.status = ClientStatus.WITH_AUDITOR
            document.item.client_reason = None
        db.add(AuditLog(
            firm_id=document.firm_id, action="document.receipt_verified",
            entity_type="document", entity_id=document.id,
            details={"duration_ms": duration_ms},
        ))
        db.flush()
        return duration_ms
