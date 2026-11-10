"""Upload safety checks after type validation: archive bounds, then malware scan.

Fail closed: when scanning is enabled and the scanner is unreachable, errors or times out, the
upload is refused and nothing is stored. Infected uploads are quarantined by rejection: no bytes
are kept or delivered; only content and signature hashes are written to the audit trail.
"""

import asyncio
import hashlib
import io
import socket
import struct
import zipfile
from typing import Protocol

from fastapi import HTTPException

from app.config import Settings

ARCHIVE_SUFFIXES = {".docx", ".xlsx"}
MAX_ARCHIVE_ENTRIES = 5_000
MAX_ARCHIVE_UNCOMPRESSED_BYTES = 500 * 1024 * 1024
MAX_ARCHIVE_RATIO = 200
CHUNK = 64 * 1024


class UploadRejected(HTTPException):
    """Rejected upload. `audit` is safe to log: hash, name, reason; never content."""

    def __init__(self, status_code: int, detail: str, audit: dict | None = None) -> None:
        super().__init__(status_code=status_code, detail=detail)
        self.audit = audit or {}


class ScanError(Exception):
    pass


class Scanner(Protocol):
    def scan(self, content: bytes) -> str | None:
        """Return the signature name if infected, None if clean. Raise ScanError on any failure."""


class ClamdScanner:
    """clamd INSTREAM over TCP. The daemon must allow StreamMaxLength >= the 100 MB upload cap."""

    def __init__(self, host: str, port: int, timeout: float) -> None:
        self.host, self.port, self.timeout = host, port, timeout

    def scan(self, content: bytes) -> str | None:
        try:
            with socket.create_connection((self.host, self.port), timeout=self.timeout) as sock:
                sock.settimeout(self.timeout)
                sock.sendall(b"zINSTREAM\0")
                for start in range(0, len(content), CHUNK):
                    chunk = content[start : start + CHUNK]
                    sock.sendall(struct.pack("!I", len(chunk)) + chunk)
                sock.sendall(struct.pack("!I", 0))
                reply = b""
                while not reply.endswith(b"\0") and len(reply) < 4096:
                    part = sock.recv(1024)
                    if not part:
                        break
                    reply += part
        except OSError as exc:
            raise ScanError("scanner unreachable") from exc
        text = reply.rstrip(b"\0").decode("utf-8", "replace").strip()
        if text.endswith("OK"):
            return None
        if text.endswith("FOUND"):
            return text.removeprefix("stream:").removesuffix("FOUND").strip() or "unknown"
        raise ScanError("scanner returned an error")


def get_scanner(settings: Settings) -> Scanner | None:
    if settings.upload_scan_mode == "clamav":
        return ClamdScanner(
            settings.clamd_host, settings.clamd_port, settings.upload_scan_timeout_seconds
        )
    return None


def check_archive_bounds(content: bytes, suffix: str) -> None:
    """Office files are zip archives: reject encrypted, oversized-when-expanded or bomb-like ones.

    Reads only the archive directory; nothing is decompressed.
    """
    if suffix not in ARCHIVE_SUFFIXES:
        return
    try:
        entries = zipfile.ZipFile(io.BytesIO(content)).infolist()
    except zipfile.BadZipFile:
        raise UploadRejected(422, "File is damaged. Please upload the original file.") from None
    total = sum(e.file_size for e in entries)
    if (
        len(entries) > MAX_ARCHIVE_ENTRIES
        or total > MAX_ARCHIVE_UNCOMPRESSED_BYTES
        or any(e.flag_bits & 0x1 for e in entries)
        or total > MAX_ARCHIVE_RATIO * max(len(content), 1)
    ):
        raise UploadRejected(422, "File cannot be accepted. Please upload the original file.")


async def screen_upload(
    settings: Settings,
    content: bytes,
    *,
    suffix: str,
    sha256: str,
    filename: str,
    scanner: Scanner | None = None,
) -> None:
    # User filenames and scanner-provided text may contain private content.
    del filename
    check_archive_bounds(content, suffix)
    scanner = scanner or get_scanner(settings)
    if scanner is None:
        return
    try:
        signature = await asyncio.to_thread(scanner.scan, content)
    except ScanError:
        raise UploadRejected(
            503,
            "Upload could not be checked right now. Please try again later.",
            {"reason": "scan_failed", "sha256": sha256},
        ) from None
    if signature is not None:
        raise UploadRejected(
            422,
            "This file was blocked by a safety check. Please contact your auditor.",
            {
                "reason": "quarantined",
                "signature_sha256": hashlib.sha256(signature.encode()).hexdigest(),
                "sha256": sha256,
            },
        )
