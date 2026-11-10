"""Upload scanning, quarantine and fail-closed behaviour. Harmless bounded fixtures only.

The scanner is a fake clamd speaking the INSTREAM protocol; no real antivirus or malware is used.
Real ClamAV integration is NOT RUN here.
"""

import hashlib
import io
import socket
import struct
import threading
import zipfile

import pytest
from fastapi import HTTPException

from app.config import Settings
from app.database.models import AuditLog, Document
from app.documents import get_document_ingestor
from app.documents.scanning import (
    ClamdScanner,
    ScanError,
    UploadRejected,
    check_archive_bounds,
    screen_upload,
)
from tests.test_backend_api import backend, sign_in_client  # noqa: F401

BAD = b"SYNTHETIC-INFECTED-MARKER"


class FakeClamd:
    """Minimal INSTREAM server: reports FOUND when the stream holds BAD, else OK."""

    def __init__(self, mode="scan"):
        self.mode = mode
        self.server = socket.socket()
        self.server.bind(("127.0.0.1", 0))
        self.server.listen(5)
        self.port = self.server.getsockname()[1]
        threading.Thread(target=self._serve, daemon=True).start()

    def _serve(self):
        while True:
            try:
                conn, _ = self.server.accept()
            except OSError:
                return
            with conn:
                if self.mode == "hang":
                    threading.Event().wait(3)
                    continue
                if self.mode == "drop":
                    continue
                data = b""
                buf = b""
                conn.recv(10)  # zINSTREAM\0
                while True:
                    while len(buf) < 4:
                        buf += conn.recv(65536)
                    size = struct.unpack("!I", buf[:4])[0]
                    buf = buf[4:]
                    if size == 0:
                        break
                    while len(buf) < size:
                        buf += conn.recv(65536)
                    data, buf = data + buf[:size], buf[size:]
                if self.mode == "error":
                    conn.sendall(b"INSTREAM size limit exceeded. ERROR\0")
                elif BAD in data:
                    conn.sendall(b"stream: Synthetic.Test.Signature FOUND\0")
                else:
                    conn.sendall(b"stream: OK\0")

    def close(self):
        self.server.close()


@pytest.fixture
def clamd():
    servers = []

    def make(mode="scan"):
        servers.append(FakeClamd(mode))
        return servers[-1]

    yield make
    for s in servers:
        s.close()


def settings_for(server, **kw):
    return Settings(
        _env_file=None,
        upload_scan_mode="clamav",
        clamd_port=server.port,
        upload_scan_timeout_seconds=kw.pop("timeout", 2),
        **kw,
    )


async def screen(settings, content=b"%PDF-1.4 synthetic", suffix=".pdf"):
    await screen_upload(settings, content, suffix=suffix, sha256="a" * 64, filename="f" + suffix)


async def test_clean_file_passes(clamd):
    await screen(settings_for(clamd()))


async def test_infected_file_is_quarantined_by_rejection_with_hash_only_audit(clamd):
    with pytest.raises(UploadRejected) as err:
        await screen(settings_for(clamd()), content=b"%PDF-1.4 " + BAD)
    assert err.value.status_code == 422
    assert err.value.audit["reason"] == "quarantined"
    assert (
        err.value.audit["signature_sha256"]
        == hashlib.sha256(b"Synthetic.Test.Signature").hexdigest()
    )
    assert set(err.value.audit) == {"reason", "sha256", "signature_sha256"}
    assert BAD.decode() not in str(err.value.audit)


@pytest.mark.parametrize("mode", ["error", "drop", "hang"])
async def test_scanner_failure_fails_closed(clamd, mode):
    with pytest.raises(UploadRejected) as err:
        await screen(settings_for(clamd(mode), timeout=0.5))
    assert err.value.status_code == 503
    assert err.value.audit["reason"] == "scan_failed"


async def test_unreachable_scanner_fails_closed():
    free = socket.socket()
    free.bind(("127.0.0.1", 0))
    port = free.getsockname()[1]
    free.close()
    with pytest.raises(UploadRejected) as err:
        await screen(Settings(_env_file=None, upload_scan_mode="clamav", clamd_port=port))
    assert err.value.status_code == 503


async def test_scanning_off_by_default_allows_clean_files():
    assert Settings(_env_file=None).upload_scan_mode == "off"
    await screen(Settings(_env_file=None))


def test_clamd_scanner_raises_scan_error_on_connection_refused():
    with pytest.raises(ScanError):
        ClamdScanner("127.0.0.1", 9, 0.5).scan(b"x")


def _zip(entries: dict[str, bytes], compression=zipfile.ZIP_DEFLATED) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression) as z:
        for name, data in entries.items():
            z.writestr(name, data)
    return buf.getvalue()


def test_archive_bounds_accept_normal_office_zip_and_ignore_other_types():
    check_archive_bounds(_zip({"word/document.xml": b"<w/>" * 100}), ".docx")
    check_archive_bounds(b"not a zip", ".pdf")


def test_archive_bounds_reject_damaged_and_bomb_like_archives():
    with pytest.raises(HTTPException) as damaged:
        check_archive_bounds(b"PK\x03\x04 broken", ".xlsx")
    assert damaged.value.status_code == 422
    # Highly compressible 20 MB of zeros: ratio far above the limit, built bounded and in memory.
    ratio = _zip({"a.xml": b"\0" * 20_000_000})
    with pytest.raises(HTTPException):
        check_archive_bounds(ratio, ".docx")
    many = _zip({f"f{i}.xml": b"x" for i in range(5_100)})
    with pytest.raises(HTTPException):
        check_archive_bounds(many, ".xlsx")


class ScanningIngestor:
    """Test double: real screening with a fake clamd in front of the fake storage."""

    def __init__(self, inner, settings):
        self.inner, self.settings = inner, settings

    async def ingest(self, *, engagement, item, file):
        content = await file.read()
        await file.seek(0)
        await screen_upload(
            self.settings, content, suffix=".txt", sha256="b" * 64, filename=file.filename
        )
        return await self.inner.ingest(engagement=engagement, item=item, file=file)


def _upload(client, ids, body):
    return client.post(
        f"/engagements/{ids['engagement_a']}/items/{ids['item_a']}/documents",
        files={"file": ("synthetic.txt", body, "text/plain")},
    )


@pytest.mark.parametrize("mode,body,status,action", [
    ("scan", BAD, 422, "document.quarantined"),
    ("error", b"synthetic", 503, "document.scan_failed"),
])  # fmt: skip
def test_endpoint_blocks_stores_nothing_and_audits(backend, clamd, mode, body, status, action):  # noqa: F811
    client, factory, ids, fake_ingestor, _ = backend
    settings = settings_for(clamd(mode))
    client.app.dependency_overrides[get_document_ingestor] = lambda: ScanningIngestor(
        fake_ingestor, settings
    )
    sign_in_client(client)
    response = _upload(client, ids, body)
    assert response.status_code == status
    assert BAD.decode() not in response.text
    assert fake_ingestor.calls == 0
    with factory() as db:
        assert db.query(Document).count() == 0
        log = db.query(AuditLog).filter(AuditLog.action == action).one()
        assert log.details["sha256"] == "b" * 64
        assert BAD.decode() not in str(log.details)


def test_endpoint_accepts_clean_file_through_scanner(backend, clamd):  # noqa: F811
    client, factory, ids, fake_ingestor, _ = backend
    settings = settings_for(clamd())
    client.app.dependency_overrides[get_document_ingestor] = lambda: ScanningIngestor(
        fake_ingestor, settings
    )
    sign_in_client(client)
    assert _upload(client, ids, b"synthetic clean text").status_code == 201
    assert fake_ingestor.calls == 1
