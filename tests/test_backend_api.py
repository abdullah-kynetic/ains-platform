from __future__ import annotations

import hashlib
import io
import zipfile
from collections.abc import Iterator
from datetime import UTC, date, datetime, timedelta
from urllib.parse import parse_qs, urlparse

import pyotp
import pytest
from fastapi import UploadFile
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.router import get_magic_link_sender
from app.auth.security import hash_mfa_recovery_code, hash_password
from app.checklist import ClientStatus
from app.checks.processor import DocumentProcessor
from app.config import Settings, get_settings
from app.database.models import (
    AuditLog,
    AuditorTask,
    Base,
    CheckJob,
    CheckJobStatus,
    ChecklistItemInstance,
    CheckResult,
    ClientInvitation,
    Document,
    Engagement,
    EngagementStatus,
    FindingDraft,
    Firm,
    MFARecoveryCode,
    ReviewState,
    TaskPriority,
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

    def send(
        self, *, email: str, token: str, expires_at: datetime, slug: str | None = None
    ) -> None:
        del slug
        assert email.endswith("@example.test")
        assert expires_at > datetime.now(UTC)
        self.token = token


class FakeIngestor:
    def __init__(self) -> None:
        self.calls = 0

    async def ingest(
        self, *, engagement: Engagement, item: ChecklistItemInstance | None, file: UploadFile
    ) -> StoredDocument:
        self.calls += 1
        content = await file.read()
        segment = item.item_key if item else "unassigned"
        return StoredDocument(
            egnyte_path=f"/Shared/AINS-Dev/{engagement.firm_id}/{engagement.id}/{segment}/{file.filename}",
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
        enrolling_auditor = User(
            email="enrolling-auditor@example.test",
            name="Synthetic Enrolling Auditor",
            role=UserRole.AUDITOR,
            password_hash=hash_password(AUDITOR_PASSWORD),
            mfa_enabled=False,
            accepted_at=datetime.now(UTC),
        )
        db.add_all([client_a, client_b, auditor, enrolling_auditor])
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
            enrolling_auditor=enrolling_auditor.id,
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
        invitation_preview_enabled=True,
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


def invitation_token(response_body: dict[str, object]) -> str:
    preview_path = response_body["previewPath"]
    assert isinstance(preview_path, str)
    return parse_qs(urlparse(preview_path).query)["token"][0]


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


def test_auditor_enrolls_mfa_and_uses_each_recovery_code_once(backend) -> None:
    client, factory, ids, _, _ = backend
    credentials = {
        "email": "enrolling-auditor@example.test",
        "password": AUDITOR_PASSWORD,
    }
    required = client.post("/auth/password", json=credentials)
    assert required.status_code == 403
    assert required.json()["detail"] == "Auditor MFA enrollment is required"

    client_user = client.post(
        "/auth/auditor/mfa/enrollment",
        json={"email": "alpha-client@example.test", "password": CLIENT_PASSWORD},
    )
    assert client_user.status_code == 403
    assert client_user.json()["detail"] == "Auditor access required"

    started = client.post("/auth/auditor/mfa/enrollment", json=credentials)
    assert started.status_code == 200
    start_body = started.json()
    assert "enrolling-auditor%40example.test" in start_body["provisioning_uri"]
    assert "issuer=Kien%20Solutions" in start_body["provisioning_uri"]
    assert start_body["secret"] not in client.get("/openapi.json").text

    wrong = client.post(
        "/auth/auditor/mfa/enrollment/confirm",
        json={**credentials, "code": "000000"},
    )
    assert wrong.status_code == 401

    confirmed = client.post(
        "/auth/auditor/mfa/enrollment/confirm",
        json={**credentials, "code": pyotp.TOTP(start_body["secret"]).now()},
    )
    assert confirmed.status_code == 200
    recovery_codes = confirmed.json()["recovery_codes"]
    assert confirmed.json()["user"]["role"] == "auditor"
    assert len(recovery_codes) == 10
    assert len(set(recovery_codes)) == 10
    assert client.get("/auth/session").status_code == 200

    with factory() as db:
        auditor = db.get(User, ids["enrolling_auditor"])
        records = db.scalars(
            select(MFARecoveryCode).where(MFARecoveryCode.user_id == auditor.id)
        ).all()
        assert auditor.mfa_enabled is True
        assert auditor.mfa_enrollment_expires_at is None
        assert len(records) == 10
        assert {record.code_hash for record in records} == {
            hash_mfa_recovery_code(code) for code in recovery_codes
        }
        assert all(code not in {record.code_hash for record in records} for code in recovery_codes)
        assert (
            db.scalar(
                select(AuditLog).where(
                    AuditLog.actor_id == auditor.id,
                    AuditLog.action == "auth.mfa_enrollment_completed",
                )
            )
            is not None
        )

    client.cookies.clear()
    recovery_sign_in = client.post(
        "/auth/password",
        json={**credentials, "mfa_code": recovery_codes[0]},
    )
    assert recovery_sign_in.status_code == 200
    client.cookies.clear()
    replay = client.post(
        "/auth/password",
        json={**credentials, "mfa_code": recovery_codes[0]},
    )
    assert replay.status_code == 401
    assert replay.json()["detail"] == "Invalid MFA code"


def test_auditor_mfa_enrollment_expires_and_existing_mfa_cannot_restart(backend) -> None:
    client, factory, ids, _, _ = backend
    credentials = {
        "email": "enrolling-auditor@example.test",
        "password": AUDITOR_PASSWORD,
    }
    started = client.post("/auth/auditor/mfa/enrollment", json=credentials)
    assert started.status_code == 200
    with factory() as db:
        auditor = db.get(User, ids["enrolling_auditor"])
        auditor.mfa_enrollment_expires_at = datetime.now(UTC) - timedelta(seconds=1)
        db.commit()
    expired = client.post(
        "/auth/auditor/mfa/enrollment/confirm",
        json={**credentials, "code": pyotp.TOTP(started.json()["secret"]).now()},
    )
    assert expired.status_code == 410

    already_enabled = client.post(
        "/auth/auditor/mfa/enrollment",
        json={"email": "auditor@example.test", "password": AUDITOR_PASSWORD},
    )
    assert already_enabled.status_code == 409


def test_auditor_rotates_recovery_codes_with_current_totp(backend) -> None:
    client, factory, ids, _, _ = backend
    previous_code = "AAAA-BBBB-CCCC-DDDD-EEEE-FFFF"
    with factory() as db:
        previous = MFARecoveryCode(
            user_id=ids["auditor"], code_hash=hash_mfa_recovery_code(previous_code)
        )
        db.add(previous)
        db.commit()
        previous_id = previous.id
    sign_in_auditor(client)
    assert (
        client.post("/auth/auditor/mfa/recovery-codes", json={"code": "000000"}).status_code == 401
    )
    rotated = client.post(
        "/auth/auditor/mfa/recovery-codes",
        json={"code": pyotp.TOTP(MFA_SECRET).now()},
    )
    assert rotated.status_code == 200
    codes = rotated.json()["recovery_codes"]
    assert len(codes) == 10

    client.cookies.clear()
    assert (
        client.post(
            "/auth/password",
            json={
                "email": "auditor@example.test",
                "password": AUDITOR_PASSWORD,
                "mfa_code": previous_code,
            },
        ).status_code
        == 401
    )
    with factory() as db:
        assert db.get(MFARecoveryCode, previous_id).revoked_at is not None

    sign_in_client(client)
    assert (
        client.post("/auth/auditor/mfa/recovery-codes", json={"code": "000000"}).status_code == 403
    )
    client.cookies.clear()
    recovery_sign_in = client.post(
        "/auth/password",
        json={
            "email": "auditor@example.test",
            "password": AUDITOR_PASSWORD,
            "mfa_code": codes[0],
        },
    )
    assert recovery_sign_in.status_code == 200
    with factory() as db:
        assert (
            db.scalar(
                select(AuditLog).where(
                    AuditLog.actor_id == ids["auditor"],
                    AuditLog.action == "auth.mfa_recovery_codes_rotated",
                )
            )
            is not None
        )


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


def test_manual_workspace_is_auditor_only_and_assignment_scoped(backend):
    client, factory, ids, _, _ = backend
    sign_in_client(client)
    base = f"/auditor/engagements/{ids['engagement_a']}"
    assert client.get("/auditor/engagements").status_code == 403
    assert client.get(base + "/workspace").status_code == 403
    assert client.post(base + "/initialize").status_code == 403
    assert (
        client.patch(
            base + f"/items/{ids['item_a']}/decision",
            json={"applicability": "applicable", "assessment": "supported", "notes": ""},
        ).status_code
        == 403
    )
    client.cookies.clear()
    sign_in_auditor(client)
    with factory() as db:
        db.get(Engagement, ids["engagement_b"]).auditor_id = None
        db.commit()
    other = f"/auditor/engagements/{ids['engagement_b']}"
    assert client.get(other + "/workspace").status_code == 404
    assert client.post(other + "/initialize").status_code == 404
    assert (
        client.patch(
            other + f"/items/{ids['item_b']}/decision",
            json={"applicability": "applicable", "assessment": "supported", "notes": ""},
        ).status_code
        == 404
    )
    assert [entry["id"] for entry in client.get("/auditor/engagements").json()] == [
        ids["engagement_a"]
    ]


def test_pipeline_is_auditor_only_assignment_scoped_and_audited(backend):
    client, factory, ids, _, _ = backend
    sign_in_client(client)
    assert client.get("/auditor/pipeline").status_code == 403
    path_a = f"/auditor/engagements/{ids['engagement_a']}/pipeline-stage"
    assert client.patch(path_a, json={"stage": "auditor_review"}).status_code == 403

    client.cookies.clear()
    sign_in_auditor(client)
    with factory() as db:
        db.get(Engagement, ids["engagement_b"]).auditor_id = None
        db.commit()

    body = client.get("/auditor/pipeline")
    assert body.status_code == 200
    assert [entry["id"] for entry in body.json()] == [ids["engagement_a"]]
    assert body.json()[0]["reportSigned"] is False

    denied = client.patch(
        f"/auditor/engagements/{ids['engagement_b']}/pipeline-stage",
        json={"stage": "report_drafting"},
    )
    assert denied.status_code == 404

    moved = client.patch(path_a, json={"stage": "report_drafting"})
    assert moved.status_code == 200
    assert moved.json() == {
        "id": ids["engagement_a"],
        "stage": "report_drafting",
        "reportSigned": False,
    }
    with factory() as db:
        engagement = db.get(Engagement, ids["engagement_a"])
        assert engagement.status == EngagementStatus.REPORT_DRAFTING
        event = db.scalar(
            select(AuditLog).where(
                AuditLog.firm_id == ids["firm_a"],
                AuditLog.entity_id == ids["engagement_a"],
                AuditLog.action == "engagement.pipeline_stage_changed",
            )
        )
        assert event is not None
        assert event.actor_id == ids["auditor"]
        assert event.details == {
            "before": {"stage": "document_collection"},
            "after": {"stage": "report_drafting"},
        }

    completion = client.patch(path_a, json={"stage": "complete"})
    assert completion.status_code == 409
    with factory() as db:
        assert db.get(Engagement, ids["engagement_a"]).status != EngagementStatus.COMPLETE


def test_auditor_tasks_are_assignment_scoped_and_completion_is_audited(backend):
    client, factory, ids, _, _ = backend
    with factory() as db:
        task_a = AuditorTask(
            firm_id=ids["firm_a"],
            engagement_id=ids["engagement_a"],
            assignee_id=ids["auditor"],
            title="Review synthetic replacement",
            request_id="AML-BD-004",
            due_date=date(2026, 2, 1),
            priority=TaskPriority.HIGH,
        )
        task_b = AuditorTask(
            firm_id=ids["firm_b"],
            engagement_id=ids["engagement_b"],
            assignee_id=ids["auditor"],
            title="Other tenant synthetic task",
            priority=TaskPriority.NORMAL,
        )
        db.add_all([task_a, task_b])
        db.commit()
        task_a_id, task_b_id = task_a.id, task_b.id

    sign_in_client(client)
    assert client.get("/auditor/tasks").status_code == 403
    assert client.patch(f"/auditor/tasks/{task_a_id}", json={"completed": True}).status_code == 403

    client.cookies.clear()
    sign_in_auditor(client)
    with factory() as db:
        db.get(Engagement, ids["engagement_b"]).auditor_id = None
        db.commit()

    tasks = client.get("/auditor/tasks")
    assert tasks.status_code == 200
    assert [task["id"] for task in tasks.json()] == [task_a_id]
    assert client.patch(f"/auditor/tasks/{task_b_id}", json={"completed": True}).status_code == 404

    completed = client.patch(f"/auditor/tasks/{task_a_id}", json={"completed": True})
    assert completed.status_code == 200
    assert completed.json()["id"] == task_a_id
    assert completed.json()["completed"] is True
    assert completed.json()["findingFinalized"] is False
    assert completed.json()["reportSigned"] is False
    with factory() as db:
        task = db.get(AuditorTask, task_a_id)
        assert task.completed_at is not None
        assert task.completed_by_id == ids["auditor"]
        event = db.scalar(
            select(AuditLog).where(
                AuditLog.firm_id == ids["firm_a"],
                AuditLog.entity_id == task_a_id,
                AuditLog.action == "auditor_task.completion_changed",
            )
        )
        assert event is not None
        assert event.details["before"]["completed"] is False
        assert event.details["after"]["completed"] is True


def test_auditor_creates_isolated_client_workspace_without_provisioning_access(backend):
    client, factory, ids, _, _ = backend
    payload = {
        "firm_name": " Synthetic Gamma Securities ",
        "review_period_start": "2026-01-01",
        "review_period_end": "2026-12-31",
        "due_date": "2027-02-15",
    }
    sign_in_client(client)
    assert client.post("/auditor/workspaces", json=payload).status_code == 403

    client.cookies.clear()
    sign_in_auditor(client)
    response = client.post("/auditor/workspaces", json=payload)
    assert response.status_code == 201
    body = response.json()
    assert body["firmName"] == "Synthetic Gamma Securities"
    assert body["slug"] == "synthetic-gamma-securities"
    assert body["status"] == "draft"
    assert body["requestCount"] == 34
    assert body["clientAccessProvisioned"] is False

    duplicate = client.post("/auditor/workspaces", json=payload)
    assert duplicate.status_code == 201
    assert duplicate.json()["slug"] == "synthetic-gamma-securities-2"
    assert (
        client.post(
            "/auditor/workspaces",
            json={**payload, "review_period_end": "2025-12-31"},
        ).status_code
        == 422
    )

    with factory() as db:
        engagement = db.get(Engagement, body["id"])
        assert engagement.firm_id == body["firmId"]
        assert engagement.auditor_id == ids["auditor"]
        assert len(engagement.items) == 34
        assert db.scalar(select(User).where(User.firm_id == body["firmId"])) is None
        event = db.scalar(
            select(AuditLog).where(
                AuditLog.firm_id == body["firmId"],
                AuditLog.entity_id == body["id"],
                AuditLog.action == "workspace.created",
            )
        )
        assert event is not None
        assert event.actor_id == ids["auditor"]


def test_client_invitation_is_assignment_scoped_rotated_revocable_and_single_use(backend):
    client, factory, ids, _, _ = backend
    path = f"/auditor/engagements/{ids['engagement_a']}/invitations"
    payload = {"email": "new-client@example.test", "name": "Synthetic New Client"}

    sign_in_client(client)
    assert client.post(path, json=payload).status_code == 403

    client.cookies.clear()
    sign_in_auditor(client)
    created = client.post(path, json=payload)
    assert created.status_code == 201
    body = created.json()
    assert body["firmId"] == ids["firm_a"]
    assert body["engagementId"] == ids["engagement_a"]
    assert body["status"] == "pending"
    first_token = invitation_token(body)

    listed = client.get(path)
    assert listed.status_code == 200
    assert listed.json()[0]["previewPath"] is None
    assert listed.json()[0]["email"] == payload["email"]

    resent = client.post(f"/auditor/invitations/{body['id']}/resend")
    assert resent.status_code == 200
    second_token = invitation_token(resent.json())
    assert second_token != first_token
    assert client.get(f"/auth/invitations/{first_token}").status_code == 404

    revoked = client.post(f"/auditor/invitations/{body['id']}/revoke")
    assert revoked.status_code == 200
    assert revoked.json()["status"] == "revoked"
    assert client.get(f"/auth/invitations/{second_token}").status_code == 410
    assert (
        client.post(
            "/auth/invitations/accept",
            json={"token": second_token, "password": "synthetic-password-123"},
        ).status_code
        == 410
    )

    reissued = client.post(f"/auditor/invitations/{body['id']}/resend")
    assert reissued.status_code == 200
    final_token = invitation_token(reissued.json())
    details = client.get(f"/auth/invitations/{final_token}")
    assert details.status_code == 200
    assert details.json()["firmName"] == "Synthetic Alpha Securities"
    assert details.json()["email"] == payload["email"]

    client.cookies.clear()
    accepted = client.post(
        "/auth/invitations/accept",
        json={"token": final_token, "password": "synthetic-password-123"},
    )
    assert accepted.status_code == 200
    assert accepted.json()["user"]["role"] == "client"
    assert accepted.json()["user"]["firm_id"] == ids["firm_a"]
    assert client.get("/engagements/current").json()["id"] == ids["engagement_a"]
    assert client.get(f"/engagements/{ids['engagement_b']}/questionnaire").status_code == 404
    assert (
        client.post(
            "/auth/invitations/accept",
            json={"token": final_token, "password": "synthetic-password-123"},
        ).status_code
        == 410
    )

    with factory() as db:
        invitation = db.get(ClientInvitation, body["id"])
        provisioned = db.get(User, invitation.accepted_user_id)
        assert invitation.token_hash != final_token
        assert invitation.accepted_at is not None
        assert provisioned.email == payload["email"]
        assert provisioned.firm_id == ids["firm_a"]
        assert provisioned.role == UserRole.CLIENT
        assert (
            db.scalar(
                select(AuditLog).where(
                    AuditLog.firm_id == ids["firm_a"],
                    AuditLog.entity_id == invitation.id,
                    AuditLog.action == "client_invitation.accepted",
                )
            )
            is not None
        )

    client.cookies.clear()
    sign_in_auditor(client)
    assert client.post(f"/auditor/invitations/{body['id']}/resend").status_code == 409
    assert client.post(f"/auditor/invitations/{body['id']}/revoke").status_code == 409


def test_client_invitation_expires_and_email_cannot_cross_firms(backend):
    client, factory, ids, _, _ = backend
    sign_in_auditor(client)
    path_a = f"/auditor/engagements/{ids['engagement_a']}/invitations"
    path_b = f"/auditor/engagements/{ids['engagement_b']}/invitations"
    payload = {"email": "exclusive-client@example.test", "name": "Synthetic Exclusive Client"}
    created = client.post(path_a, json=payload)
    assert created.status_code == 201
    token = invitation_token(created.json())
    assert client.post(path_b, json=payload).status_code == 409

    with factory() as db:
        invitation = db.get(ClientInvitation, created.json()["id"])
        invitation.expires_at = datetime.now(UTC) - timedelta(seconds=1)
        db.commit()
    assert client.get(f"/auth/invitations/{token}").status_code == 410

    with factory() as db:
        db.get(Engagement, ids["engagement_b"]).auditor_id = None
        db.commit()
    denied = client.post(
        path_b,
        json={"email": "unassigned-client@example.test", "name": "Synthetic Other Client"},
    )
    assert denied.status_code == 404


def test_client_invitation_preview_is_hidden_unless_explicitly_enabled(backend, monkeypatch):
    monkeypatch.setattr("app.auth.email.ResendSender.send", lambda self, **kwargs: None)
    client, _, ids, _, _ = backend
    enabled_settings = client.app.dependency_overrides[get_settings]()
    client.app.dependency_overrides[get_settings] = lambda: enabled_settings.model_copy(
        update={"invitation_preview_enabled": False}
    )
    sign_in_auditor(client)

    created = client.post(
        f"/auditor/engagements/{ids['engagement_a']}/invitations",
        json={"email": "no-preview@example.test", "name": "Synthetic No Preview"},
    )

    assert created.status_code == 201
    assert created.json()["previewPath"] is None


def test_auditor_can_create_and_edit_assigned_tasks(backend):
    client, factory, ids, _, _ = backend
    sign_in_client(client)
    assert (
        client.post(
            f"/auditor/engagements/{ids['engagement_a']}/tasks",
            json={"title": "Client must not create this"},
        ).status_code
        == 403
    )

    client.cookies.clear()
    sign_in_auditor(client)
    with factory() as db:
        db.get(Engagement, ids["engagement_b"]).auditor_id = None
        db.commit()

    denied = client.post(
        f"/auditor/engagements/{ids['engagement_b']}/tasks",
        json={"title": "Other tenant task"},
    )
    assert denied.status_code == 404

    created = client.post(
        f"/auditor/engagements/{ids['engagement_a']}/tasks",
        json={
            "title": " Draft synthetic status update ",
            "request_id": "AML-BD-004",
            "due_date": "2026-03-01",
            "priority": "high",
        },
    )
    assert created.status_code == 201
    task_id = created.json()["id"]
    assert created.json() == {
        "id": task_id,
        "engagementId": ids["engagement_a"],
        "title": "Draft synthetic status update",
        "requestId": "AML-BD-004",
        "due": "2026-03-01",
        "priority": "high",
        "assignee": "Synthetic Auditor",
        "completed": False,
    }

    updated = client.patch(
        f"/auditor/tasks/{task_id}",
        json={
            "title": "Finalize synthetic status update",
            "request_id": None,
            "due_date": None,
            "priority": "low",
        },
    )
    assert updated.status_code == 200
    assert updated.json()["title"] == "Finalize synthetic status update"
    assert updated.json()["requestId"] is None
    assert updated.json()["due"] is None
    assert updated.json()["priority"] == "low"
    assert updated.json()["findingFinalized"] is False
    assert updated.json()["reportSigned"] is False
    assert client.patch(f"/auditor/tasks/{task_id}", json={}).status_code == 422
    assert client.patch(f"/auditor/tasks/{task_id}", json={"title": "  "}).status_code == 422

    with factory() as db:
        task = db.get(AuditorTask, task_id)
        assert task.firm_id == ids["firm_a"]
        assert task.engagement_id == ids["engagement_a"]
        assert task.assignee_id == ids["auditor"]
        assert task.title == "Finalize synthetic status update"
        assert task.request_id is None
        assert task.due_date is None
        assert task.priority == TaskPriority.LOW
        events = db.scalars(
            select(AuditLog)
            .where(
                AuditLog.firm_id == ids["firm_a"],
                AuditLog.entity_id == task_id,
                AuditLog.action.in_(["auditor_task.created", "auditor_task.updated"]),
            )
            .order_by(AuditLog.created_at)
        ).all()
        assert [event.action for event in events] == [
            "auditor_task.created",
            "auditor_task.updated",
        ]


def test_auditor_activity_is_assignment_scoped_and_omits_internal_details(backend):
    client, factory, ids, _, _ = backend
    with factory() as db:
        db.add_all(
            [
                AuditLog(
                    firm_id=ids["firm_a"],
                    actor_id=ids["auditor"],
                    action="request.manual_decision",
                    entity_type="checklist_item_instance",
                    entity_id=ids["item_a"],
                    details={"notes": "Sensitive synthetic internal reasoning"},
                ),
                AuditLog(
                    firm_id=ids["firm_b"],
                    actor_id=ids["auditor"],
                    action="request.manual_decision",
                    entity_type="checklist_item_instance",
                    entity_id=ids["item_b"],
                    details={"notes": "Other tenant internal reasoning"},
                ),
            ]
        )
        db.get(Engagement, ids["engagement_b"]).auditor_id = None
        db.commit()

    sign_in_client(client)
    assert client.get("/auditor/activity").status_code == 403
    client.cookies.clear()
    sign_in_auditor(client)

    response = client.get("/auditor/activity")
    assert response.status_code == 200
    assert len(response.json()) == 1
    event = response.json()[0]
    assert event["subject"] == "AML-BD-004"
    assert event["engagementId"] == ids["engagement_a"]
    assert event["kind"] == "review"
    assert "Sensitive synthetic internal reasoning" not in response.text
    assert "Other tenant" not in response.text


@pytest.mark.parametrize(
    "assessment", ["supported", "partial", "conflicting", "unable_to_determine"]
)
def test_manual_decision_history_and_client_privacy(backend, assessment):
    client, _, ids, _, _ = backend
    sign_in_auditor(client)
    base = f"/auditor/engagements/{ids['engagement_a']}"
    decision = {
        "applicability": "applicable",
        "assessment": assessment,
        "notes": "Synthetic internal auditor reasoning",
    }
    response = client.patch(base + f"/items/{ids['item_a']}/decision", json=decision)
    assert response.status_code == 200
    workspace = client.get(base + "/workspace").json()
    item = next(item for item in workspace["requests"] if item["id"] == ids["item_a"])
    assert item["assessment"] == assessment and item["applicability"] == "applicable"
    event = next(
        row for row in reversed(workspace["history"]) if row["action"] == "request.manual_decision"
    )
    assert event["actorId"] == ids["auditor"]
    assert event["details"]["before"]["assessment"] is None
    assert event["details"]["after"] == decision
    assert not workspace["readiness"]["ready"]
    client.cookies.clear()
    sign_in_client(client)
    text = client.get("/engagements/current").text
    assert "Synthetic internal auditor reasoning" not in text
    assert '"assessment"' not in text


def test_manual_na_cannot_have_assessment_and_needs_notes(backend):
    client, _, ids, _, _ = backend
    sign_in_auditor(client)
    path = f"/auditor/engagements/{ids['engagement_a']}/items/{ids['item_a']}/decision"
    assert (
        client.patch(
            path,
            json={
                "applicability": "not_applicable",
                "assessment": "supported",
                "notes": "Synthetic rationale",
            },
        ).status_code
        == 422
    )
    assert (
        client.patch(
            path, json={"applicability": "not_applicable", "assessment": None, "notes": ""}
        ).status_code
        == 422
    )


def test_initialize_from_catalog_and_complete_readiness(backend):
    client, factory, ids, _, _ = backend
    with factory() as db:
        engagement = Engagement(
            firm_id=ids["firm_a"],
            auditor_id=ids["auditor"],
            review_period_start=date(2025, 1, 1),
            review_period_end=date(2025, 12, 31),
        )
        db.add(engagement)
        db.commit()
        engagement_id = engagement.id
    sign_in_auditor(client)
    base = f"/auditor/engagements/{engagement_id}"
    assert client.post(base + "/initialize").json() == {"requests": 34}
    with factory() as db:
        initialized = db.get(Engagement, engagement_id)
        assert initialized.checklist_version == "aml_bd_v1"
        assert len(initialized.checklist_snapshot["requests"]) == 34
        snapshot = initialized.checklist_snapshot
    assert client.post(base + "/initialize").status_code == 409
    with factory() as db:
        assert db.get(Engagement, engagement_id).checklist_snapshot == snapshot
    workspace = client.get(base + "/workspace").json()
    assert len(workspace["requests"]) == 34 and not workspace["readiness"]["ready"]
    with factory() as db:
        for item in db.scalars(
            select(ChecklistItemInstance).where(
                ChecklistItemInstance.engagement_id == engagement_id
            )
        ):
            item.applicability_decision = "not_applicable"
            item.internal_notes = "Synthetic test only"
        db.commit()
    assert client.get(base + "/workspace").json()["readiness"]["ready"]


def test_new_upload_invalidates_previous_evidence_assessment(backend):
    client, factory, ids, _, _ = backend
    with factory() as db:
        db.get(ChecklistItemInstance, ids["item_a"]).assessment = "supported"
        db.commit()
    sign_in_client(client)
    response = client.post(
        f"/engagements/{ids['engagement_a']}/items/{ids['item_a']}/documents",
        files={"file": ("synthetic.txt", b"synthetic replacement")},
    )
    assert response.status_code == 201
    with factory() as db:
        assert db.get(ChecklistItemInstance, ids["item_a"]).assessment is None


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
        assert item.representation == "no_activity" and item.status == ClientStatus.NOT_APPLICABLE


def test_questionnaire_refuses_no_answers_even_with_a_representation(backend):
    client, factory, ids, _, _ = backend
    with factory() as db:
        db.get(ChecklistItemInstance, ids["item_a"]).item_key = "AML-BD-012"
        db.commit()
    sign_in_client(client)
    path = f"/engagements/{ids['engagement_a']}/questionnaire/answers"
    answer = {"itemId": ids["item_a"], "applies": False}
    assert client.post(path, json={"answers": [answer]}).status_code == 422
    answer["representation"] = "no_activity"
    assert client.post(path, json={"answers": [answer]}).status_code == 422
    with factory() as db:
        item = db.get(ChecklistItemInstance, ids["item_a"])
        assert item.applicable and item.status != ClientStatus.NOT_APPLICABLE


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
    response = client.post(
        path + "/feedback", json={"code": "unreadable", "document_id": uploaded["id"]}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "action_needed_reupload"
    assert (
        client.post(
            path + "/feedback", json={"code": "audit_finding", "document_id": uploaded["id"]}
        ).status_code
        == 422
    )
    assert client.post(path + "/follow-up").status_code == 200
    with factory() as db:
        db.get(Engagement, ids["engagement_b"]).auditor_id = None
        db.commit()
    other = f"/auditor/engagements/{ids['engagement_b']}/items/{ids['item_b']}"
    assert client.post(other + "/follow-up").status_code == 404
    assert (
        client.post(
            other + "/feedback", json={"code": "unreadable", "document_id": uploaded["id"]}
        ).status_code
        == 404
    )


def test_questionnaire_no_longer_marks_na_and_the_old_review_route_is_gone(backend) -> None:
    client, factory, ids, _, _ = backend
    sign_in_client(client)
    questionnaire = client.get(f"/engagements/{ids['engagement_a']}/questionnaire")
    assert questionnaire.status_code == 200
    assert len(questionnaire.json()["questions"]) == 1

    # A "No" answer is refused with a pointer to the reasoned N/A flow, and changes nothing.
    refused = client.post(
        f"/engagements/{ids['engagement_a']}/questionnaire/answers",
        json={"answers": [{"itemId": ids["item_a"], "applies": False}]},
    )
    assert refused.status_code == 422
    assert "document checklist" in refused.json()["detail"]
    with factory() as db:
        item = db.get(ChecklistItemInstance, ids["item_a"])
        assert item and item.applicable and item.status != ClientStatus.NOT_APPLICABLE

    # "Yes, this applies" still works.
    ok = client.post(
        f"/engagements/{ids['engagement_a']}/questionnaire/answers",
        json={"answers": [{"itemId": ids["item_a"], "applies": True}]},
    )
    assert ok.status_code == 200

    # The older auditor review route no longer exists for anyone.
    review = f"/engagements/{ids['engagement_a']}/questionnaire/items/{ids['item_a']}/na-review"
    assert client.post(review, json={"decision": "approve"}).status_code in {404, 405}
    client.cookies.clear()
    sign_in_auditor(client)
    assert client.post(review, json={"decision": "approve"}).status_code in {404, 405}
    assert client.post(review, json={"decision": "reject"}).status_code in {404, 405}


def test_questionnaire_answers_are_tenant_scoped(backend) -> None:
    client, _, ids, _, _ = backend
    sign_in_client(client)
    response = client.post(
        f"/engagements/{ids['engagement_b']}/questionnaire/answers",
        json={"answers": [{"itemId": ids["item_b"], "applies": False}]},
    )
    assert response.status_code == 404


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


async def test_late_receipt_verification_preserves_replacement_feedback(backend):
    client, factory, ids, _, _ = backend
    sign_in_client(client)
    content = b"Synthetic late receipt"
    client.post(
        f"/engagements/{ids['engagement_a']}/items/{ids['item_a']}/documents",
        files={"file": ("synthetic.txt", content, "text/plain")},
    )
    processor = DocumentProcessor(
        check_settings(), client_factory=lambda _: FakeDownloadClient(content)
    )
    with factory() as db:
        item = db.get(ChecklistItemInstance, ids["item_a"])
        item.status = ClientStatus.ACTION_NEEDED_REUPLOAD
        item.client_reason = "Please replace with a readable copy."
        await processor.process(db, db.scalar(select(Document)).id)
        assert item.status == ClientStatus.ACTION_NEEDED_REUPLOAD
        assert item.client_reason == "Please replace with a readable copy."


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
    assert (
        docx.headers["content-disposition"]
        == f'attachment; filename="kien-{ids["engagement_a"]}-draft-report.docx"'
    )
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
    assert (
        pdf.headers["content-disposition"]
        == f'attachment; filename="kien-{ids["engagement_a"]}-draft-report.pdf"'
    )


def test_unconfigured_invitation_delivery_does_not_persist_invite(backend):
    client, factory, ids, _, _ = backend
    settings = client.app.dependency_overrides[get_settings]()
    client.app.dependency_overrides[get_settings] = lambda: settings.model_copy(
        update={"invitation_preview_enabled": False}
    )
    sign_in_auditor(client)
    response = client.post(
        f"/auditor/engagements/{ids['engagement_a']}/invitations",
        json={"email": "delivery-unconfigured@example.test", "name": "Synthetic"},
    )
    assert response.status_code == 503
    with factory() as db:
        assert (
            db.scalar(
                select(ClientInvitation).where(
                    ClientInvitation.email == "delivery-unconfigured@example.test"
                )
            )
            is None
        )


def test_unassigned_upload_is_engagement_owned_and_queued(backend):
    client, factory, ids, _, _ = backend
    sign_in_client(client)
    response = client.post(
        f"/engagements/{ids['engagement_a']}/documents",
        files={"file": ("synthetic.txt", b"synthetic unassigned evidence")},
    )
    assert response.status_code == 201
    with factory() as db:
        document = db.get(Document, response.json()["id"])
        assert document.firm_id == ids["firm_a"]
        assert document.engagement_id == ids["engagement_a"]
        assert document.item_instance_id is None
        assert document.check_job is not None
    view = client.get("/engagements/current").json()
    assert view["unassignedDocuments"][0]["id"] == response.json()["id"]


def test_unassigned_upload_rejects_other_firm(backend):
    client, _, ids, ingestor, _ = backend
    sign_in_client(client)
    response = client.post(
        f"/engagements/{ids['engagement_b']}/documents",
        files={"file": ("synthetic.txt", b"synthetic")},
    )
    assert response.status_code == 404
    assert ingestor.calls == 0


async def test_unassigned_receipt_verification(backend):
    client, factory, ids, _, _ = backend
    sign_in_client(client)
    content = b"Synthetic unassigned receipt"
    response = client.post(
        f"/engagements/{ids['engagement_a']}/documents",
        files={"file": ("synthetic.txt", content)},
    )
    assert response.status_code == 201
    processor = DocumentProcessor(
        check_settings(), client_factory=lambda _: FakeDownloadClient(content)
    )
    with factory() as db:
        await processor.process(db, response.json()["id"])
        db.commit()
        assert db.scalar(select(CheckResult)).status == "received"
        assert db.get(Document, response.json()["id"]).item is None


def test_unassigned_upload_rejects_unassigned_auditor(backend):
    client, factory, ids, ingestor, _ = backend
    with factory() as db:
        db.get(Engagement, ids["engagement_b"]).auditor_id = None
        db.commit()
    sign_in_auditor(client)
    response = client.post(
        f"/engagements/{ids['engagement_b']}/documents",
        files={"file": ("synthetic.txt", b"synthetic")},
    )
    assert response.status_code == 404
    assert ingestor.calls == 0
