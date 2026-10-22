from __future__ import annotations

import hashlib
import io
import zipfile
from collections.abc import Iterator
from datetime import UTC, date, datetime

import pyotp
import pytest
from fastapi import UploadFile
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.router import get_magic_link_sender
from app.auth.security import hash_password
from app.checklist import ClientStatus
from app.checks.processor import DocumentProcessor
from app.config import Settings, get_settings
from app.database.models import (
    Base,
    CheckJob,
    CheckJobStatus,
    ChecklistItemInstance,
    CheckResult,
    Document,
    Engagement,
    FindingDraft,
    Firm,
    ReviewState,
    User,
    UserRole,
)
from app.database.session import get_db
from app.documents import StoredDocument, get_document_ingestor
from app.main import create_app
from app.worker import run_once

CLIENT_PASSWORD = "synthetic-client-password"
AUDITOR_PASSWORD = "synthetic-auditor-password"
MFA_SECRET = "JBSWY3DPEHPK3PXP"


class CaptureMagicLinkSender:
    def __init__(self) -> None:
        self.token: str | None = None

    def send(self, *, email: str, token: str, expires_at: datetime) -> None:
        assert email.endswith("@example.test")
        assert expires_at > datetime.now(UTC)
        self.token = token


class FakeIngestor:
    def __init__(self) -> None:
        self.calls = 0

    async def ingest(
        self, *, engagement: Engagement, item: ChecklistItemInstance, file: UploadFile
    ) -> StoredDocument:
        self.calls += 1
        content = await file.read()
        return StoredDocument(
            egnyte_path=f"/Shared/AINS-Dev/{engagement.firm_id}/{engagement.id}/{item.item_key}/{file.filename}",
            sha256=hashlib.sha256(content).hexdigest(),
            size_bytes=len(content),
            version="synthetic-v1",
        )


class FakeDownloadClient:
    def __init__(self, content: bytes) -> None:
        self.content = content
        self.paths: list[str] = []

    async def download_file(self, path: str) -> bytes:
        self.paths.append(path)
        return self.content

    async def aclose(self) -> None:
        return None


def check_settings() -> Settings:
    return Settings(
        _env_file=None,
        session_secret=SecretStr("synthetic-test-session-secret-at-least-32-bytes"),
        document_check_timeout_seconds=30,
    )


@pytest.fixture
def backend() -> Iterator[
    tuple[TestClient, sessionmaker[Session], dict[str, str], FakeIngestor, CaptureMagicLinkSender]
]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    ids: dict[str, str] = {}
    with factory() as db:
        firm_a = Firm(name="Synthetic Alpha Securities", slug="synthetic-alpha")
        firm_b = Firm(name="Synthetic Beta Securities", slug="synthetic-beta")
        db.add_all([firm_a, firm_b])
        db.flush()
        client_a = User(
            firm_id=firm_a.id,
            email="alpha-client@example.test",
            name="Synthetic Alpha Client",
            role=UserRole.CLIENT,
            password_hash=hash_password(CLIENT_PASSWORD),
            accepted_at=datetime.now(UTC),
        )
        client_b = User(
            firm_id=firm_b.id,
            email="beta-client@example.test",
            name="Synthetic Beta Client",
            role=UserRole.CLIENT,
            password_hash=hash_password(CLIENT_PASSWORD),
            accepted_at=datetime.now(UTC),
        )
        auditor = User(
            email="auditor@example.test",
            name="Synthetic Auditor",
            role=UserRole.AUDITOR,
            password_hash=hash_password(AUDITOR_PASSWORD),
            mfa_secret=MFA_SECRET,
            mfa_enabled=True,
            accepted_at=datetime.now(UTC),
        )
        db.add_all([client_a, client_b, auditor])
        db.flush()
        engagement_a = Engagement(
            firm_id=firm_a.id,
            auditor_id=auditor.id,
            review_period_start=date(2025, 1, 1),
            review_period_end=date(2025, 12, 31),
            due_date=date(2026, 2, 15),
        )
        engagement_b = Engagement(
            firm_id=firm_b.id,
            auditor_id=auditor.id,
            review_period_start=date(2025, 1, 1),
            review_period_end=date(2025, 12, 31),
        )
        db.add_all([engagement_a, engagement_b])
        db.flush()
        item_a = ChecklistItemInstance(
            firm_id=firm_a.id,
            engagement_id=engagement_a.id,
            item_key="AML-BD-004",
            section_key="governance",
            section_title="AML program and governance",
            title="Written AML program",
            description="Synthetic current program.",
            position=1,
            is_conditional=True,
            condition_question="Does the firm maintain a written AML program?",
        )
        restricted_a = ChecklistItemInstance(
            firm_id=firm_a.id,
            engagement_id=engagement_a.id,
            item_key="AML-BD-017",
            section_key="restricted",
            section_title="Restricted materials",
            title="SAR-related material",
            description="Coordinate directly with the auditor.",
            position=2,
            status=ClientStatus.RESTRICTED_DO_NOT_UPLOAD,
            restricted=True,
        )
        item_b = ChecklistItemInstance(
            firm_id=firm_b.id,
            engagement_id=engagement_b.id,
            item_key="AML-BD-004",
            section_key="governance",
            section_title="AML program and governance",
            title="Written AML program",
            description="Other tenant synthetic program.",
            position=1,
        )
        db.add_all([item_a, restricted_a, item_b])
        db.commit()
        ids.update(
            firm_a=firm_a.id,
            firm_b=firm_b.id,
            client_a=client_a.id,
            client_b=client_b.id,
            auditor=auditor.id,
            engagement_a=engagement_a.id,
            engagement_b=engagement_b.id,
            item_a=item_a.id,
            item_b=item_b.id,
            restricted_a=restricted_a.id,
        )

    settings = Settings(
        _env_file=None,
        database_url="sqlite+pysqlite:///:memory:",
        session_secret=SecretStr("synthetic-test-session-secret-at-least-32-bytes"),
        session_cookie_secure=False,
        cors_origins="http://localhost:3000",
    )
    fake_ingestor = FakeIngestor()
    magic_sender = CaptureMagicLinkSender()

    def db_override() -> Iterator[Session]:
        with factory() as db:
            yield db

    app = create_app()
    app.dependency_overrides[get_db] = db_override
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_document_ingestor] = lambda: fake_ingestor
    app.dependency_overrides[get_magic_link_sender] = lambda: magic_sender
    with TestClient(app) as client:
        yield client, factory, ids, fake_ingestor, magic_sender
    engine.dispose()


def sign_in_client(client: TestClient, email: str = "alpha-client@example.test") -> None:
    response = client.post("/auth/password", json={"email": email, "password": CLIENT_PASSWORD})
    assert response.status_code == 200


def sign_in_auditor(client: TestClient) -> None:
    response = client.post(
        "/auth/password",
        json={
            "email": "auditor@example.test",
            "password": AUDITOR_PASSWORD,
            "mfa_code": pyotp.TOTP(MFA_SECRET).now(),
        },
    )
    assert response.status_code == 200


def test_invite_only_password_session_and_sign_out(backend) -> None:
    client, _, _, _, _ = backend
    unknown = client.post(
        "/auth/password",
        json={"email": "not-invited@example.test", "password": CLIENT_PASSWORD},
    )
    assert unknown.status_code == 401

    sign_in_client(client)
    session = client.get("/auth/session")
    assert session.status_code == 200
    assert session.json()["user"]["role"] == "client"
    assert client.post("/auth/sign-out").status_code == 204
    assert client.get("/auth/session").status_code == 401


def test_auditor_requires_mfa(backend) -> None:
    client, _, _, _, _ = backend
    without_mfa = client.post(
        "/auth/password",
        json={"email": "auditor@example.test", "password": AUDITOR_PASSWORD},
    )
    assert without_mfa.status_code == 401
    assert without_mfa.json()["detail"] == "MFA code required"

    response = client.post(
        "/auth/password",
        json={
            "email": "auditor@example.test",
            "password": AUDITOR_PASSWORD,
            "mfa_code": pyotp.TOTP(MFA_SECRET).now(),
        },
    )
    assert response.status_code == 200
    assert response.json()["user"]["role"] == "auditor"


def test_magic_link_is_single_use(backend) -> None:
    client, _, _, _, sender = backend
    requested = client.post("/auth/magic-link", json={"email": "alpha-client@example.test"})
    assert requested.status_code == 202 and sender.token

    verified = client.post("/auth/magic-link/verify", json={"token": sender.token})
    assert verified.status_code == 200
    replay = client.post("/auth/magic-link/verify", json={"token": sender.token})
    assert replay.status_code == 401


def test_current_engagement_is_tenant_scoped_and_client_safe(backend) -> None:
    client, _, ids, _, _ = backend
    sign_in_client(client)
    response = client.get("/engagements/current")
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == ids["engagement_a"]
    assert body["firmName"] == "Synthetic Alpha Securities"
    assert "finding" not in str(body).casefold()
    assert {item["id"] for section in body["sections"] for item in section["items"]} == {
        ids["item_a"],
        ids["restricted_a"],
    }


def test_upload_rejects_cross_tenant_and_restricted_items(backend) -> None:
    client, _, ids, ingestor, _ = backend
    sign_in_client(client)
    other = client.post(
        f"/engagements/{ids['engagement_b']}/items/{ids['item_b']}/documents",
        files={"file": ("synthetic.txt", b"synthetic")},
    )
    assert other.status_code == 404
    restricted = client.post(
        f"/engagements/{ids['engagement_a']}/items/{ids['restricted_a']}/documents",
        files={"file": ("synthetic.txt", b"synthetic")},
    )
    assert restricted.status_code == 403
    assert ingestor.calls == 0


def test_upload_persists_tenant_owned_document_and_sets_checking(backend) -> None:
    client, factory, ids, ingestor, _ = backend
    sign_in_client(client)
    response = client.post(
        f"/engagements/{ids['engagement_a']}/items/{ids['item_a']}/documents",
        files={"file": ("synthetic.txt", b"synthetic content", "text/plain")},
    )
    assert response.status_code == 201
    assert response.json()["status"] == "checking"
    assert ingestor.calls == 1
    with factory() as db:
        document = db.scalar(select(Document))
        check_job = db.scalar(select(CheckJob))
        item = db.get(ChecklistItemInstance, ids["item_a"])
        assert document and document.firm_id == ids["firm_a"]
        assert check_job and check_job.document_id == document.id
        assert document.sha256 == hashlib.sha256(b"synthetic content").hexdigest()
        assert item and item.status == ClientStatus.CHECKING


def test_upload_rejects_inapplicable_request_without_storage(backend):
    client, factory, ids, ingestor, _ = backend
    sign_in_client(client)
    with factory() as db:
        db.get(ChecklistItemInstance, ids["item_a"]).applicable = False
        db.commit()
    response = client.post(
        f"/engagements/{ids['engagement_a']}/items/{ids['item_a']}/documents",
        files={"file": ("synthetic.txt", b"synthetic")},
    )
    assert response.status_code == 404
    assert ingestor.calls == 0


def test_representation_is_tenant_scoped_and_requires_confirmation(backend):
    client, factory, ids, _, _ = backend
    sign_in_client(client)
    path = f"/engagements/{ids['engagement_a']}/items/{ids['item_a']}/representations"
    assert client.post(path, json={"kind": "no_activity", "confirmed": False}).status_code == 422
    other = f"/engagements/{ids['engagement_b']}/items/{ids['item_b']}/representations"
    assert client.post(other, json={"kind": "no_activity", "confirmed": True}).status_code == 404
    assert client.post(path, json={"kind": "no_activity", "confirmed": True}).status_code == 200
    with factory() as db:
        item = db.get(ChecklistItemInstance, ids["item_a"])
        assert item.representation == "no_activity" and item.na_review_state.value == "pending"


def test_auditor_follow_up_and_document_replacement_feedback(backend):
    client, factory, ids, _, _ = backend
    sign_in_client(client)
    uploaded = client.post(
        f"/engagements/{ids['engagement_a']}/items/{ids['item_a']}/documents",
        files={"file": ("synthetic.txt", b"synthetic")},
    ).json()
    path = f"/auditor/engagements/{ids['engagement_a']}/items/{ids['item_a']}"
    assert client.post(path + "/follow-up").status_code == 403
    client.cookies.clear()
    sign_in_auditor(client)
    response = client.post(path + "/feedback", json={
        "code": "unreadable", "document_id": uploaded["id"]})
    assert response.status_code == 200
    assert response.json()["status"] == "action_needed_reupload"
    assert client.post(path + "/feedback", json={
        "code": "audit_finding", "document_id": uploaded["id"]}).status_code == 422
    assert client.post(path + "/follow-up").status_code == 200
    with factory() as db:
        db.get(Engagement, ids["engagement_b"]).auditor_id = None
        db.commit()
    other = f"/auditor/engagements/{ids['engagement_b']}/items/{ids['item_b']}"
    assert client.post(other + "/follow-up").status_code == 404
    assert client.post(other + "/feedback", json={
        "code": "unreadable", "document_id": uploaded["id"]}).status_code == 404


def test_questionnaire_no_answer_remains_visible_pending_auditor_review(backend) -> None:
    client, factory, ids, _, _ = backend
    sign_in_client(client)
    questionnaire = client.get(f"/engagements/{ids['engagement_a']}/questionnaire")
    assert questionnaire.status_code == 200
    assert questionnaire.json()["questions"] == [
        {
            "itemId": ids["item_a"],
            "sectionTitle": "Transactions and payments",
            "question": "Does the firm use clearing-firm AML reports?",
            "answer": None,
            "naReviewState": None,
            "whenNo": "proposed_not_applicable",
            "representation": None,
        }
    ]

    answered = client.post(
        f"/engagements/{ids['engagement_a']}/questionnaire/answers",
        json={"answers": [{"itemId": ids["item_a"], "applies": False}]},
    )
    assert answered.status_code == 200
    assert answered.json()["questions"][0]["naReviewState"] == "pending"
    visible_ids = {
        item["id"]
        for section in client.get("/engagements/current").json()["sections"]
        for item in section["items"]
    }
    assert ids["item_a"] in visible_ids
    with factory() as db:
        item = db.get(ChecklistItemInstance, ids["item_a"])
        assert item and not item.applicable and item.na_review_state.value == "pending"


def test_only_assigned_auditor_can_reject_na_and_restore_item(backend) -> None:
    client, factory, ids, _, _ = backend
    sign_in_client(client)
    client.post(
        f"/engagements/{ids['engagement_a']}/questionnaire/answers",
        json={"answers": [{"itemId": ids["item_a"], "applies": False}]},
    )
    forbidden = client.post(
        f"/engagements/{ids['engagement_a']}/questionnaire/items/{ids['item_a']}/na-review",
        json={"decision": "reject"},
    )
    assert forbidden.status_code == 403

    client.cookies.clear()
    sign_in_auditor(client)
    reviewed = client.post(
        f"/engagements/{ids['engagement_a']}/questionnaire/items/{ids['item_a']}/na-review",
        json={"decision": "reject"},
    )
    assert reviewed.status_code == 200
    assert reviewed.json()["naReviewState"] == "rejected"
    with factory() as db:
        item = db.get(ChecklistItemInstance, ids["item_a"])
        assert item and item.applicable and item.status == ClientStatus.REQUESTED
        assert item.na_approved_by_id == ids["auditor"]


def test_questionnaire_answers_are_tenant_scoped(backend) -> None:
    client, _, ids, _, _ = backend
    sign_in_client(client)
    response = client.post(
        f"/engagements/{ids['engagement_b']}/questionnaire/answers",
        json={"answers": [{"itemId": ids["item_b"], "applies": False}]},
    )
    assert response.status_code == 404


def test_assigned_auditor_can_approve_na(backend) -> None:
    client, factory, ids, _, _ = backend
    sign_in_client(client)
    client.post(
        f"/engagements/{ids['engagement_a']}/questionnaire/answers",
        json={"answers": [{"itemId": ids["item_a"], "applies": False}]},
    )
    client.cookies.clear()
    sign_in_auditor(client)
    response = client.post(
        f"/engagements/{ids['engagement_a']}/questionnaire/items/{ids['item_a']}/na-review",
        json={"decision": "approve"},
    )
    assert response.status_code == 200
    assert response.json()["naReviewState"] == "approved"
    with factory() as db:
        item = db.get(ChecklistItemInstance, ids["item_a"])
        assert item and not item.applicable and item.na_approved_by_id == ids["auditor"]


async def test_worker_marks_durable_job_succeeded(backend) -> None:
    client, factory, ids, _, _ = backend
    sign_in_client(client)
    client.post(
        f"/engagements/{ids['engagement_a']}/items/{ids['item_a']}/documents",
        files={"file": ("synthetic.txt", b"synthetic", "text/plain")},
    )

    class StubProcessor:
        async def process(self, db: Session, document_id: str) -> int:
            assert db.get(Document, document_id)
            return 42

    with factory() as db:
        assert await run_once(db, check_settings(), processor=StubProcessor())
    with factory() as db:
        job = db.scalar(select(CheckJob))
        assert job and job.status == CheckJobStatus.SUCCEEDED
        assert job.duration_ms == 42 and job.attempts == 1

async def test_receipt_worker_verifies_fingerprint_without_audit_decision(backend) -> None:
    client, factory, ids, _, _ = backend
    sign_in_client(client)
    content = b"Synthetic receipt verification fixture"
    response = client.post(
        f"/engagements/{ids['engagement_a']}/items/{ids['item_a']}/documents",
        files={"file": ("synthetic.txt", content, "text/plain")},
    )
    assert response.status_code == 201
    processor = DocumentProcessor(
        check_settings(), client_factory=lambda _: FakeDownloadClient(content)
    )
    with factory() as db:
        document = db.scalar(select(Document))
        await processor.process(db, document.id)
        db.commit()
        receipt = db.scalar(select(CheckResult))
        assert receipt.check_type == "storage_receipt"
        assert receipt.status == "received"
        assert receipt.details == {"sha256_verified": True}
        assert db.get(ChecklistItemInstance, ids["item_a"]).status == ClientStatus.WITH_AUDITOR


async def test_receipt_worker_rejects_changed_storage_bytes(backend) -> None:
    client, factory, ids, _, _ = backend
    sign_in_client(client)
    client.post(
        f"/engagements/{ids['engagement_a']}/items/{ids['item_a']}/documents",
        files={"file": ("synthetic.txt", b"Synthetic original", "text/plain")},
    )
    processor = DocumentProcessor(
        check_settings(), client_factory=lambda _: FakeDownloadClient(b"Synthetic changed")
    )
    with factory() as db:
        document = db.scalar(select(Document))
        with pytest.raises(ValueError, match="fingerprint_mismatch"):
            await processor.process(db, document.id)

def test_auditor_queue_and_finding_review_are_role_scoped(backend) -> None:
    client, factory, ids, _, _ = backend
    sign_in_client(client)
    client.post(
        f"/engagements/{ids['engagement_a']}/items/{ids['item_a']}/documents",
        files={"file": ("synthetic.txt", b"synthetic evidence", "text/plain")},
    )
    with factory() as db:
        document = db.scalar(select(Document))
        item = db.get(ChecklistItemInstance, ids["item_a"])
        assert document and item
        item.status = ClientStatus.WITH_AUDITOR
        db.add(
            CheckResult(
                firm_id=ids["firm_a"],
                document_id=document.id,
                check_type="synthetic_check",
                status="completed",
                details={"synthetic": True},
                citations=[{"page": 1, "quote": "synthetic evidence"}],
            )
        )
        finding = FindingDraft(
            firm_id=ids["firm_a"],
            engagement_id=ids["engagement_a"],
            document_id=document.id,
            title="Synthetic draft finding",
            body="Synthetic body for auditor review.",
            severity="low",
            citations=[{"page": 1, "quote": "synthetic evidence"}],
        )
        db.add(finding)
        db.commit()
        finding_id = finding.id

    assert client.get("/auditor/queue").status_code == 403
    client.cookies.clear()
    sign_in_auditor(client)
    queue = client.get("/auditor/queue")
    assert queue.status_code == 200
    assert queue.json()[0]["findings"][0]["id"] == finding_id
    assert queue.json()[0]["evidence"][0]["checks"][0]["checkType"] == "synthetic_check"

    reviewed = client.patch(
        f"/auditor/findings/{finding_id}",
        json={
            "action": "edit",
            "title": "Auditor-edited synthetic finding",
            "severity": "high",
            "citations": [{"page": 1, "quote": "auditor verified synthetic evidence"}],
        },
    )
    assert reviewed.status_code == 200
    assert reviewed.json()["reviewState"] == "edited"
    assert reviewed.json()["severity"] == "high"
    with factory() as db:
        finding = db.get(FindingDraft, finding_id)
        assert finding and finding.reviewed_by_id == ids["auditor"]


def test_auditor_cannot_accept_finding_without_citation(backend) -> None:
    client, factory, ids, _, _ = backend
    sign_in_client(client)
    client.post(
        f"/engagements/{ids['engagement_a']}/items/{ids['item_a']}/documents",
        files={"file": ("synthetic.txt", b"synthetic evidence", "text/plain")},
    )
    with factory() as db:
        document = db.scalar(select(Document))
        assert document
        finding = FindingDraft(
            firm_id=ids["firm_a"],
            engagement_id=ids["engagement_a"],
            document_id=document.id,
            title="Synthetic uncited draft",
            body="Must not be accepted without a citation.",
            severity="low",
            citations=[],
        )
        db.add(finding)
        db.commit()
        finding_id = finding.id
    client.cookies.clear()
    sign_in_auditor(client)
    response = client.patch(f"/auditor/findings/{finding_id}", json={"action": "accept"})
    assert response.status_code == 422


def test_draft_report_includes_only_auditor_approved_findings(backend) -> None:
    client, factory, ids, _, _ = backend
    sign_in_client(client)
    client.post(
        f"/engagements/{ids['engagement_a']}/items/{ids['item_a']}/documents",
        files={"file": ("synthetic.txt", b"synthetic evidence", "text/plain")},
    )
    with factory() as db:
        document = db.scalar(select(Document))
        assert document
        db.add_all(
            [
                FindingDraft(
                    firm_id=ids["firm_a"],
                    engagement_id=ids["engagement_a"],
                    document_id=document.id,
                    title="Approved synthetic finding",
                    body="Approved synthetic report body.",
                    severity="moderate",
                    citations=[{"page": 1, "quote": "approved synthetic evidence"}],
                    review_state=ReviewState.ACCEPTED,
                    reviewed_by_id=ids["auditor"],
                ),
                FindingDraft(
                    firm_id=ids["firm_a"],
                    engagement_id=ids["engagement_a"],
                    document_id=document.id,
                    title="Rejected synthetic finding",
                    body="This must not appear in a report.",
                    severity="low",
                    citations=[{"page": 1, "quote": "rejected synthetic evidence"}],
                    review_state=ReviewState.REJECTED,
                    reviewed_by_id=ids["auditor"],
                ),
            ]
        )
        db.commit()

    assert (
        client.post(f"/auditor/engagements/{ids['engagement_a']}/report?format=pdf").status_code
        == 403
    )
    client.cookies.clear()
    sign_in_auditor(client)
    docx = client.post(f"/auditor/engagements/{ids['engagement_a']}/report?format=docx")
    assert docx.status_code == 200
    assert docx.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    with zipfile.ZipFile(io.BytesIO(docx.content)) as archive:
        xml = archive.read("word/document.xml").decode()
    assert "Approved synthetic finding" in xml
    assert "Rejected synthetic finding" not in xml
    assert "DRAFT" in xml and "not signed" in xml

    pdf = client.post(f"/auditor/engagements/{ids['engagement_a']}/report?format=pdf")
    assert pdf.status_code == 200
    assert pdf.content.startswith(b"%PDF-")
