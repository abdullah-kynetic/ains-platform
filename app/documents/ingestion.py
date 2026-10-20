"""Validated upload ingestion through the guarded Egnyte client."""

from __future__ import annotations

import hashlib
import re
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import PurePath
from typing import Annotated, Protocol

from fastapi import Depends, HTTPException, UploadFile

from app.config import Settings, get_settings
from app.database.models import ChecklistItemInstance, Engagement
from app.egnyte_client import (
    SIMPLE_UPLOAD_MAX_BYTES,
    EgnyteClient,
    EgnyteConfigError,
    EgnyteError,
)

ALLOWED_EXTENSIONS = {
    ".csv",
    ".doc",
    ".docx",
    ".jpeg",
    ".jpg",
    ".pdf",
    ".png",
    ".tif",
    ".tiff",
    ".txt",
    ".xls",
    ".xlsx",
}
MAGIC_PREFIXES: dict[str, tuple[bytes, ...]] = {
    ".pdf": (b"%PDF-",),
    ".png": (b"\x89PNG\r\n\x1a\n",),
    ".jpg": (b"\xff\xd8\xff",),
    ".jpeg": (b"\xff\xd8\xff",),
    ".tif": (b"II*\x00", b"MM\x00*"),
    ".tiff": (b"II*\x00", b"MM\x00*"),
    ".doc": (b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1",),
    ".xls": (b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1",),
    ".docx": (b"PK\x03\x04",),
    ".xlsx": (b"PK\x03\x04",),
}
READ_CHUNK_BYTES = 1024 * 1024


@dataclass(frozen=True)
class StoredDocument:
    egnyte_path: str
    sha256: str
    size_bytes: int
    version: str = "1"


class DocumentIngestor(Protocol):
    async def ingest(
        self, *, engagement: Engagement, item: ChecklistItemInstance, file: UploadFile
    ) -> StoredDocument: ...


class EgnyteStorageClient(Protocol):
    async def create_folder(self, path: str, *, exist_ok: bool = True) -> dict: ...

    async def upload_file(self, path: str, data: bytes) -> dict: ...

    async def aclose(self) -> None: ...


def _safe_segment(value: str, *, fallback: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip()).strip(".-")
    return (cleaned or fallback)[:120]


def _validated_filename(filename: str | None) -> tuple[str, str]:
    if not filename or filename in {".", ".."} or "\x00" in filename:
        raise HTTPException(status_code=422, detail="Upload must have a valid file name")
    if PurePath(filename).name != filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=422, detail="File name must not contain a path")
    suffix = PurePath(filename).suffix.casefold()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail="Unsupported file type. Upload PDF, images, Office files, CSV, or text.",
        )
    stem = _safe_segment(filename[: -len(suffix)], fallback="document")
    return f"{stem}{suffix}", suffix


async def _read_validated(file: UploadFile, suffix: str) -> tuple[bytes, str]:
    content = bytearray()
    digest = hashlib.sha256()
    while chunk := await file.read(READ_CHUNK_BYTES):
        content.extend(chunk)
        digest.update(chunk)
        if len(content) > SIMPLE_UPLOAD_MAX_BYTES:
            raise HTTPException(status_code=413, detail="File exceeds the 100 MB upload limit")
    if not content:
        raise HTTPException(status_code=422, detail="File is empty")
    prefixes = MAGIC_PREFIXES.get(suffix)
    if prefixes and not any(content.startswith(prefix) for prefix in prefixes):
        raise HTTPException(
            status_code=422,
            detail="File content does not match its extension. Please upload the original file.",
        )
    return bytes(content), digest.hexdigest()


class EgnyteDocumentIngestor:
    def __init__(
        self,
        settings: Settings,
        *,
        client_factory: Callable[[Settings], EgnyteStorageClient] = EgnyteClient.from_settings,
    ) -> None:
        self.settings = settings
        self.client_factory = client_factory

    async def ingest(
        self, *, engagement: Engagement, item: ChecklistItemInstance, file: UploadFile
    ) -> StoredDocument:
        safe_name, suffix = _validated_filename(file.filename)
        accepted = {
            extension.casefold() if extension.startswith(".") else f".{extension.casefold()}"
            for extension in item.accepted_extensions
        }
        if accepted and suffix not in accepted:
            raise HTTPException(
                status_code=415,
                detail="This file type is not accepted for this checklist item.",
            )
        content, sha256 = await _read_validated(file, suffix)
        root = self.settings.egnyte_dev_root.rstrip("/")
        firm = _safe_segment(engagement.firm.slug, fallback=engagement.firm_id)
        engagement_segment = _safe_segment(engagement.id, fallback="engagement")
        item_segment = _safe_segment(item.item_key, fallback=item.id)
        folder = f"{root}/{firm}/{engagement_segment}/{item_segment}"
        upload_id = uuid.uuid4().hex[:12]
        remote_path = f"{folder}/{upload_id}-{safe_name}"

        client: EgnyteStorageClient | None = None
        try:
            client = self.client_factory(self.settings)
            current = root
            for segment in (firm, engagement_segment, item_segment):
                current = f"{current}/{segment}"
                await client.create_folder(current, exist_ok=True)
            result = await client.upload_file(remote_path, content)
        except EgnyteConfigError:
            raise HTTPException(
                status_code=503, detail="Egnyte document storage is not configured"
            ) from None
        except EgnyteError:
            raise HTTPException(
                status_code=502, detail="Egnyte document storage rejected the upload"
            ) from None
        finally:
            if client is not None:
                await client.aclose()

        version = str(
            result.get("entry_id") or result.get("group_id") or result.get("checksum") or upload_id
        )
        return StoredDocument(
            egnyte_path=remote_path,
            sha256=sha256,
            size_bytes=len(content),
            version=version,
        )


IngestSettings = Annotated[Settings, Depends(get_settings)]


def get_document_ingestor(settings: IngestSettings) -> DocumentIngestor:
    return EgnyteDocumentIngestor(settings)
