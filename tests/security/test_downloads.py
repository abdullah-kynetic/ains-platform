"""S-19: every download is authorized on that request and links are short-lived."""

from urllib.parse import parse_qs, urlparse

import boto3
import pytest
from moto import mock_aws
from sqlalchemy import select

from app.api.downloads import LINK_SECONDS, get_storage
from app.config import Settings
from app.database.models import AuditLog, ChecklistItemInstance, Document, Engagement
from app.storage.s3 import S3Storage
from tests.test_backend_api import backend, sign_in_auditor, sign_in_client  # noqa: F401

BETA = "beta-client@example.test"


@pytest.fixture
def stored(backend, monkeypatch):  # noqa: F811
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    client, factory, ids, *_ = backend
    with mock_aws():
        settings = Settings(_env_file=None, s3_bucket="synthetic-documents")
        boto3.client("s3", region_name="us-east-1").create_bucket(Bucket=settings.s3_bucket)
        storage = S3Storage(settings)
        client.app.dependency_overrides[get_storage] = lambda: storage
        with factory() as db:
            doc = Document(
                firm_id=ids["firm_a"],
                engagement_id=ids["engagement_a"],
                item_instance_id=ids["item_a"],
                uploaded_by_id=ids["client_a"],
                original_name="synthetic.txt",
                size_bytes=3,
                egnyte_path=f"s3://synthetic-documents/firms/{ids['firm_a']}/e/item/synthetic.txt",
                sha256="a" * 64,
                version="1",
                number="1.1",
            )
            db.add(doc)
            db.commit()
            ids["doc"] = doc.id
        yield client, factory, ids


def paths(ids):
    tail = f"engagements/{ids['engagement_a']}/documents/{ids['doc']}/download"
    return f"/{tail}", f"/auditor/{tail}"


def test_assigned_auditor_and_own_firm_client_get_short_lived_links(stored):
    client, factory, ids = stored
    own, auditor = paths(ids)
    sign_in_client(client)
    link = client.get(own)
    assert link.status_code == 200, link.text
    url = link.json()["url"]
    query = parse_qs(urlparse(url).query)
    assert query["X-Amz-Expires"] == [str(LINK_SECONDS)] and LINK_SECONDS <= 300
    assert f"/firms/{ids['firm_a']}/" in url
    client.cookies.clear()
    sign_in_auditor(client)
    assert client.get(auditor).status_code == 200
    with factory() as db:
        rows = db.scalars(
            select(AuditLog).where(AuditLog.action == "document.download_authorized")
        ).all()
        assert len(rows) == 2 and not any("X-Amz" in str(r.details) for r in rows)


def test_anonymous_other_firm_wrong_role_and_unassigned_are_denied(stored):
    client, factory, ids = stored
    own, auditor = paths(ids)
    assert client.get(own).status_code == 401 and client.get(auditor).status_code == 401
    sign_in_client(client, BETA)
    assert client.get(own).status_code == 404  # real document id, other firm
    assert client.get(auditor).status_code == 403
    client.cookies.clear()
    sign_in_client(client)
    assert client.get(auditor).status_code == 403
    client.cookies.clear()
    sign_in_auditor(client)
    assert client.get(own).status_code in {403, 404}
    with factory() as db:
        db.get(Engagement, ids["engagement_a"]).auditor_id = ids["enrolling_auditor"]
        db.commit()
    assert client.get(auditor).status_code == 404  # authorization is checked on every request


def test_receipt_of_another_firm_or_restricted_item_is_never_signed(stored):
    client, factory, ids = stored
    own, _ = paths(ids)
    sign_in_client(client)
    with factory() as db:
        db.get(
            Document, ids["doc"]
        ).egnyte_path = f"s3://synthetic-documents/firms/{ids['firm_b']}/e/item/synthetic.txt"
        db.commit()
    assert client.get(own).status_code == 404
    with factory() as db:
        doc = db.get(Document, ids["doc"])
        doc.egnyte_path = f"s3://synthetic-documents/firms/{ids['firm_a']}/e/i/x.txt"
        db.get(ChecklistItemInstance, ids["item_a"]).restricted = True
        db.commit()
    assert client.get(own).status_code == 404
