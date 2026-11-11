"""L2-7: retention rule, firm export, erasure of stored files, and R2 uploads without VersionId."""

import io
from datetime import UTC, date, datetime, timedelta

import boto3
import pytest
from botocore.exceptions import ClientError
from fastapi import UploadFile
from moto import mock_aws
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.config import Settings
from app.database.models import (
    AuditLog,
    Base,
    ChecklistItemInstance,
    Document,
    Engagement,
    EngagementSignoff,
    EngagementStatus,
    Firm,
    Invoice,
    InvoiceIssuer,
    User,
    UserRole,
)
from app.documents.ingestion import get_document_ingestor
from app.retention import ERASED_PREFIX, erase_firm_files, export_firm_data, plan_erasure
from app.storage.s3 import S3Storage

BUCKET = "synthetic-retention"


@pytest.fixture
def world(monkeypatch):
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    with mock_aws():
        settings = Settings(_env_file=None, s3_bucket=BUCKET, record_retention_days=100)
        boto3.client("s3", region_name="us-east-1").create_bucket(
            Bucket=BUCKET, ObjectLockEnabledForBucket=True
        )
        storage = S3Storage(settings)
        engine = create_engine("sqlite://")
        Base.metadata.create_all(engine)
        factory = sessionmaker(engine, expire_on_commit=False)
        with factory() as db:
            firm_a, firm_b = (
                Firm(name="Synthetic A", slug="syn-a"),
                Firm(name="Synthetic B", slug="syn-b"),
            )
            db.add_all([firm_a, firm_b])
            db.flush()
            auditor = User(email="a@example.test", name="Auditor", role=UserRole.AUDITOR)
            client = User(
                email="c@example.test", name="Client", role=UserRole.CLIENT, firm_id=firm_a.id
            )
            db.add_all([auditor, client])
            db.flush()

            def engagement(firm, status, **kw):
                e = Engagement(
                    firm_id=firm.id,
                    auditor_id=auditor.id,
                    status=status,
                    review_period_start=date(2025, 1, 1),
                    review_period_end=date(2025, 12, 31),
                    **kw,
                )
                db.add(e)
                db.flush()
                return e

            def document(e, firm, name):
                key = f"{e.id}/x/{name}"
                storage.put(firm.id, key, b"synthetic " + name.encode())
                row = Document(
                    firm_id=firm.id,
                    engagement_id=e.id,
                    uploaded_by_id=client.id,
                    original_name=name,
                    size_bytes=10,
                    egnyte_path=f"s3://{BUCKET}/{storage.key(firm.id, key)}",
                    sha256="d" * 64,
                    version="1",
                    number="1.1",
                )
                db.add(row)
                db.flush()
                return row

            open_e = engagement(firm_a, EngagementStatus.COLLECTING)
            recent = engagement(firm_a, EngagementStatus.COMPLETE)
            old = engagement(firm_a, EngagementStatus.COMPLETE)
            other = engagement(firm_b, EngagementStatus.COLLECTING)
            for e, days in ((recent, 10), (old, 400)):
                db.add(
                    EngagementSignoff(
                        firm_id=firm_a.id,
                        engagement_id=e.id,
                        independence_answers=[],
                        partner_signed_at=datetime.now(UTC) - timedelta(days=days),
                        completed_at=datetime.now(UTC) - timedelta(days=days),
                        partner_fingerprint="f" * 64,
                        signed_sections=[
                            {"id": "scope", "title": "Scope", "body": "Public text"},
                            {"id": "finding-1", "title": "Finding", "body": "SECRET FINDING"},
                        ],
                    )
                )
            docs = {
                "open": document(open_e, firm_a, "open.txt"),
                "recent": document(recent, firm_a, "recent.txt"),
                "old": document(old, firm_a, "old.txt"),
                "other": document(other, firm_b, "other.txt"),
            }
            db.add(
                ChecklistItemInstance(
                    firm_id=firm_a.id,
                    engagement_id=open_e.id,
                    item_key="AML-BD-001",
                    section_key="s",
                    section_title="S",
                    title="Written program",
                )
            )
            db.commit()
            ids = {
                "firm_a": firm_a.id,
                "firm_b": firm_b.id,
                "docs": {k: d.id for k, d in docs.items()},
                "open": open_e.id,
            }
        yield settings, storage, factory, ids


def _exists(storage, firm, path):
    try:
        storage.client.head_object(Bucket=BUCKET, Key=path)
        return True
    except ClientError:
        return False


def test_plan_retains_recent_completed_engagements_only(world):
    settings, storage, factory, ids = world
    with factory() as db:
        plan = plan_erasure(db, ids["firm_a"], settings)
        eligible = {d.original_name for d in plan.eligible}
        assert eligible == {"open.txt", "old.txt"}
        assert [r for _, r in plan.retained][0].startswith("engagement completed; kept until")
        assert plan.summary()["eligible"] == 2 and plan.summary()["retained"] == 1


def test_erase_needs_confirm_and_removes_all_versions_only_for_eligible_files(world):
    settings, storage, factory, ids = world
    storage.put(ids["firm_a"], f"{ids['open']}/x/open.txt", b"second version")  # a 2nd version
    with factory() as db:
        dry = erase_firm_files(db, storage, ids["firm_a"], settings, confirm=False)
        assert dry["erased"] == 0 and dry["confirmed"] is False
        assert not db.scalars(select(AuditLog).where(AuditLog.action == "firm_data.erased")).all()
    with factory() as db:
        done = erase_firm_files(db, storage, ids["firm_a"], settings, confirm=True)
        assert done["erased"] == 2 and done["failed"] == 0 and done["retained"] == 1
    with factory() as db:
        rows = {d.original_name: d for d in db.scalars(select(Document))}
        assert rows["open.txt"].egnyte_path == f"{ERASED_PREFIX}{rows['open.txt'].id}"
        assert rows["old.txt"].egnyte_path.startswith(ERASED_PREFIX)
        assert rows["recent.txt"].egnyte_path.startswith("s3://")  # retained
        assert rows["other.txt"].egnyte_path.startswith("s3://")  # another firm
        assert rows["open.txt"].sha256 == "d" * 64  # fingerprint stays
        log = db.scalar(select(AuditLog).where(AuditLog.action == "firm_data.erased"))
        assert log.firm_id == ids["firm_a"] and log.details["erased"] == 2
    versions = storage.client.list_object_versions(Bucket=BUCKET, Prefix="firms/")
    left = {v["Key"] for v in versions.get("Versions", [])}
    assert not any("open.txt" in k or "old.txt" in k for k in left)
    assert any("recent.txt" in k for k in left) and any("other.txt" in k for k in left)
    with factory() as db:  # idempotent
        again = erase_firm_files(db, storage, ids["firm_a"], settings, confirm=True)
        assert again["erased"] == 0 and again["eligible"] == 0


def test_erase_never_records_a_deletion_that_failed(world, monkeypatch):
    settings, storage, factory, ids = world

    def refuse(self, path):
        raise ClientError({"Error": {"Code": "AccessDenied", "Message": "locked"}}, "DeleteObject")

    monkeypatch.setattr(S3Storage, "delete_receipt", refuse)
    with factory() as db:
        result = erase_firm_files(db, storage, ids["firm_a"], settings, confirm=True)
        assert result["erased"] == 0 and result["failed"] == 2
    with factory() as db:
        assert all(d.egnyte_path.startswith("s3://") for d in db.scalars(select(Document)))


def test_export_is_client_visible_only_and_scoped_to_the_firm(world):
    settings, storage, factory, ids = world
    with factory() as db:
        issuer = InvoiceIssuer(
            id="iss",
            auditor_id=db.scalar(select(User.id).where(User.role == UserRole.AUDITOR)),
            next_number=2,
        )
        db.add(issuer)
        db.flush()
        today = datetime.now(UTC).date()
        for number, status in ((1, "sent"), (2, "draft")):
            db.add(
                Invoice(
                    issuer_id="iss",
                    firm_id=ids["firm_a"],
                    auditor_id=issuer.auditor_id,
                    number=number,
                    status=status,
                    issue_date=today,
                    due_date=today,
                    subtotal_cents=100,
                    total_cents=100,
                )
            )
        db.commit()
        data = export_firm_data(db, ids["firm_a"])
    text = str(data)
    assert data["firm"]["name"] == "Synthetic A"
    assert [u["email"] for u in data["users"]] == ["c@example.test"]
    assert [i["number"] for i in data["invoices"]] == ["KIEN-0001"]
    assert "SECRET FINDING" not in text and "Synthetic B" not in text and "other.txt" not in text
    assert "password" not in text.lower() and "mfa" not in text.lower()
    signed = [e for e in data["engagements"] if e["signedReport"]]
    assert len(signed) == 2 and [s["title"] for s in signed[0]["signedReport"]["sections"]] == [
        "Scope"
    ]
    open_e = next(e for e in data["engagements"] if e["id"] == ids["open"])
    assert open_e["checklist"][0]["request"] == "AML-BD-001"
    assert (
        open_e["documents"][0]["sha256"] == "d" * 64 and open_e["documents"][0]["erased"] is False
    )
    with pytest.raises(ValueError):
        with factory() as db:
            export_firm_data(db, "missing")


async def test_r2_upload_without_version_id_still_ingests(world, monkeypatch):
    settings, storage, factory, ids = world
    monkeypatch.setattr(S3Storage, "put", lambda self, firm, path, content, **kw: {})
    from types import SimpleNamespace

    engagement = SimpleNamespace(id="e1", firm_id="firm-a")
    item = SimpleNamespace(
        engagement_id="e1",
        firm_id="firm-a",
        item_key="AML-01",
        restricted=False,
        accepted_extensions=["txt"],
    )
    stored = await get_document_ingestor(settings).ingest(
        engagement=engagement,
        item=item,
        file=UploadFile(filename="s.txt", file=io.BytesIO(b"synthetic")),
    )
    assert stored.version == "1" and stored.egnyte_path.startswith(f"s3://{BUCKET}/firms/firm-a/")
