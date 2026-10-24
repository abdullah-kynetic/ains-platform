"""Synthetic S3 integration including tenant boundaries and immutable report versions."""

import hashlib
import io
from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse

import boto3
import pytest
from fastapi import HTTPException, UploadFile
from moto import mock_aws

from app.config import Settings
from app.documents.ingestion import S3DocumentIngestor, get_document_ingestor
from app.storage.s3 import S3Storage


@pytest.fixture
def storage(monkeypatch):
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    with mock_aws():
        settings = Settings(
            _env_file=None,
            s3_bucket="synthetic-documents",
            s3_retention_days=7,
        )
        boto3.client("s3", region_name="us-east-1").create_bucket(
            Bucket=settings.s3_bucket, ObjectLockEnabledForBucket=True
        )
        yield S3Storage(settings)


def test_encryption_versioning_retention_and_signed_urls(storage):
    receipt = storage.put("firm-a", "reports/final.pdf", b"synthetic", final_report=True)
    head = storage.client.head_object(
        Bucket=storage.settings.s3_bucket,
        Key="firms/firm-a/reports/final.pdf",
        VersionId=receipt["VersionId"],
    )
    assert head["ServerSideEncryption"] == "AES256"
    assert head["ObjectLockMode"] == "GOVERNANCE"
    storage.put("firm-a", "intake/file.txt", b"synthetic")
    head = storage.client.head_object(
        Bucket=storage.settings.s3_bucket, Key="firms/firm-a/intake/file.txt"
    )
    assert "ObjectLockMode" not in head
    for upload in (True, False):
        url = storage.presign("firm-a", "intake/file.txt", upload=upload)
        assert "/firms/firm-a/intake/file.txt" in url
        assert parse_qs(urlparse(url).query)["X-Amz-Expires"] == ["300"]
    for firm, path in [("../firm-b", "x"), ("firm-a", "../firm-b/x"), ("firm-a", "/x")]:
        with pytest.raises(ValueError):
            storage.presign(firm, path)


def test_kms_and_compliance(storage):
    storage.settings.s3_sse = "aws:kms"
    storage.settings.s3_kms_key_id = "alias/synthetic"
    storage.settings.s3_retention_mode = "COMPLIANCE"
    storage.put("firm-a", "reports/final.pdf", b"synthetic", final_report=True)
    head = storage.client.head_object(
        Bucket=storage.settings.s3_bucket, Key="firms/firm-a/reports/final.pdf"
    )
    assert head["ServerSideEncryption"] == "aws:kms"
    assert head["ObjectLockMode"] == "COMPLIANCE"


async def test_ingestion_and_firm_denial(storage):
    engagement = SimpleNamespace(id="engagement-a", firm_id="firm-a")
    item = SimpleNamespace(
        engagement_id="engagement-a",
        firm_id="firm-a",
        item_key="AML-01",
        restricted=False,
        accepted_extensions=["txt"],
    )
    ingestor = get_document_ingestor(storage.settings)
    assert isinstance(ingestor, S3DocumentIngestor)
    document = await ingestor.ingest(
        engagement=engagement,
        item=item,
        file=UploadFile(filename="synthetic.txt", file=io.BytesIO(b"synthetic")),
    )
    assert document.sha256 == hashlib.sha256(b"synthetic").hexdigest()
    assert await storage.download_file(document.egnyte_path) == b"synthetic"
    item.firm_id = "firm-b"
    with pytest.raises(HTTPException) as denied:
        await ingestor.ingest(
            engagement=engagement,
            item=item,
            file=UploadFile(filename="synthetic.txt", file=io.BytesIO(b"x")),
        )
    assert denied.value.status_code == 404
    with pytest.raises(ValueError):
        await storage.download_file("s3://other-bucket/firms/firm-a/x")


def test_storage_selection_defaults_to_s3_and_egnyte_is_explicit(monkeypatch):
    from app.checks.processor import DocumentProcessor
    from app.documents.ingestion import EgnyteDocumentIngestor
    from app.egnyte_client import EgnyteClient

    monkeypatch.delenv("STORAGE_BACKEND", raising=False)
    settings = Settings(_env_file=None)
    assert settings.storage_backend == "s3"
    assert isinstance(get_document_ingestor(settings), S3DocumentIngestor)
    assert DocumentProcessor(settings).client_factory is S3Storage
    monkeypatch.setenv("STORAGE_BACKEND", "egnyte")
    settings = Settings(_env_file=None)
    assert isinstance(get_document_ingestor(settings), EgnyteDocumentIngestor)
    assert DocumentProcessor(settings).client_factory == EgnyteClient.from_settings
