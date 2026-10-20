from __future__ import annotations

import hashlib
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

from app.api.engagements import StoredDocument, get_document_ingestor
from app.auth.router import get_magic_link_sender
from app.auth.security import hash_password
from app.checklist import ClientStatus
from app.config import Settings, get_settings
from app.database.models import (
    Base,
    ChecklistItemInstance,
    Document,
    Engagement,
    Firm,
    User,
    UserRole,
)
from app.database.session import get_db
from app.main import create_app

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
            item_key="aml-program",
            section_key="governance",
            section_title="AML program and governance",
            title="Written AML program",
            description="Synthetic current program.",
            position=1,
        )
        restricted_a = ChecklistItemInstance(
            firm_id=firm_a.id,
            engagement_id=engagement_a.id,
            item_key="sar-material",
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
            item_key="aml-program",
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
        item = db.get(ChecklistItemInstance, ids["item_a"])
        assert document and document.firm_id == ids["firm_a"]
        assert document.sha256 == hashlib.sha256(b"synthetic content").hexdigest()
        assert item and item.status == ClientStatus.CHECKING
