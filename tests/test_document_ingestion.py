from __future__ import annotations

import hashlib
import io
from datetime import date

import pytest
from fastapi import HTTPException, UploadFile
from pydantic import SecretStr

import app.documents.ingestion as ingestion
from app.config import Settings
from app.database.models import ChecklistItemInstance, Engagement, Firm
from app.documents.ingestion import EgnyteDocumentIngestor


class FakeEgnyteClient:
    def __init__(self) -> None:
        self.folders: list[str] = []
        self.uploads: list[tuple[str, bytes]] = []
        self.closed = False

    async def create_folder(self, path: str, *, exist_ok: bool = True) -> dict:
        assert exist_ok
        self.folders.append(path)
        return {"path": path}

    async def upload_file(self, path: str, data: bytes) -> dict:
        self.uploads.append((path, data))
        return {"entry_id": "egnyte-version-synthetic"}

    async def aclose(self) -> None:
        self.closed = True


def settings() -> Settings:
    return Settings(
        _env_file=None,
        egnyte_domain="synthetic",
        egnyte_api_key=SecretStr("synthetic-client-id"),
        egnyte_client_secret=SecretStr("synthetic-client-secret"),
        egnyte_username="synthetic-user",
        egnyte_password=SecretStr("synthetic-password"),
        egnyte_dev_root="/Shared/AINS-Dev",
    )


def records() -> tuple[Engagement, ChecklistItemInstance]:
    firm = Firm(id="firm-synthetic", name="Synthetic Firm", slug="synthetic-firm")
    engagement = Engagement(
        id="engagement-synthetic",
        firm_id=firm.id,
        firm=firm,
        review_period_start=date(2025, 1, 1),
        review_period_end=date(2025, 12, 31),
    )
    item = ChecklistItemInstance(
        id="item-synthetic",
        firm_id=firm.id,
        engagement_id=engagement.id,
        item_key="aml-program",
        section_key="governance",
        section_title="Governance",
        title="Written AML program",
        accepted_extensions=["pdf", "docx"],
    )
    return engagement, item


def upload(filename: str, content: bytes) -> UploadFile:
    return UploadFile(filename=filename, file=io.BytesIO(content))


async def test_ingestor_validates_hashes_and_stores_under_guarded_hierarchy() -> None:
    client = FakeEgnyteClient()
    service = EgnyteDocumentIngestor(settings(), client_factory=lambda _: client)
    engagement, item = records()
    content = b"%PDF-1.7\nsynthetic document only"

    result = await service.ingest(
        engagement=engagement,
        item=item,
        file=upload("Synthetic AML Program.pdf", content),
    )

    assert client.folders == [
        "/Shared/AINS-Dev/synthetic-firm",
        "/Shared/AINS-Dev/synthetic-firm/engagement-synthetic",
        "/Shared/AINS-Dev/synthetic-firm/engagement-synthetic/aml-program",
    ]
    remote, sent = client.uploads[0]
    assert remote.startswith("/Shared/AINS-Dev/synthetic-firm/engagement-synthetic/aml-program/")
    assert remote.endswith("-Synthetic-AML-Program.pdf")
    assert sent == content
    assert result.egnyte_path == remote
    assert result.sha256 == hashlib.sha256(content).hexdigest()
    assert result.version == "egnyte-version-synthetic"
    assert client.closed


@pytest.mark.parametrize(
    ("filename", "content", "expected_status"),
    [
        ("../escape.pdf", b"%PDF-1.7", 422),
        ("malware.exe", b"MZ", 415),
        ("fake.pdf", b"not a pdf", 422),
        ("empty.pdf", b"", 422),
    ],
)
async def test_ingestor_rejects_invalid_files_before_egnyte(
    filename: str, content: bytes, expected_status: int
) -> None:
    client = FakeEgnyteClient()
    service = EgnyteDocumentIngestor(settings(), client_factory=lambda _: client)
    engagement, item = records()
    with pytest.raises(HTTPException) as error:
        await service.ingest(engagement=engagement, item=item, file=upload(filename, content))
    assert error.value.status_code == expected_status
    assert not client.folders and not client.uploads


async def test_ingestor_rejects_oversized_file(monkeypatch) -> None:
    monkeypatch.setattr(ingestion, "SIMPLE_UPLOAD_MAX_BYTES", 4)
    client = FakeEgnyteClient()
    service = EgnyteDocumentIngestor(settings(), client_factory=lambda _: client)
    engagement, item = records()
    with pytest.raises(HTTPException) as error:
        await service.ingest(
            engagement=engagement, item=item, file=upload("large.pdf", b"%PDF-1.7")
        )
    assert error.value.status_code == 413
    assert not client.uploads


async def test_ingestor_enforces_item_specific_file_types() -> None:
    client = FakeEgnyteClient()
    service = EgnyteDocumentIngestor(settings(), client_factory=lambda _: client)
    engagement, item = records()
    with pytest.raises(HTTPException) as error:
        await service.ingest(
            engagement=engagement,
            item=item,
            file=upload("synthetic.csv", b"column\nvalue\n"),
        )
    assert error.value.status_code == 415
    assert not client.uploads


async def test_ingestor_reports_missing_egnyte_configuration_safely() -> None:
    unconfigured = settings()
    unconfigured.egnyte_domain = ""
    service = EgnyteDocumentIngestor(unconfigured)
    engagement, item = records()
    with pytest.raises(HTTPException) as error:
        await service.ingest(
            engagement=engagement,
            item=item,
            file=upload("synthetic.pdf", b"%PDF-1.7\nsynthetic"),
        )
    assert error.value.status_code == 503
    assert error.value.detail == "Egnyte document storage is not configured"
