from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
import respx
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.email import ResendSender
from app.auth.security import hash_password, verify_password
from app.config import Settings, get_settings
from app.database.models import AuthSession, Base, PasswordResetToken, User, UserRole
from app.database.session import get_db
from app.main import create_app


@pytest.fixture
def reset_backend():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)
    with factory() as db:
        user = User(
            email="synthetic@example.test",
            name="Synthetic",
            role=UserRole.AUDITOR,
            password_hash=hash_password("old-synthetic-password"),
        )
        db.add(user)
        db.flush()
        db.add(AuthSession(user_id=user.id, expires_at=datetime.now(UTC) + timedelta(hours=1)))
        db.commit()
    settings = Settings(
        _env_file=None,
        resend_api_key=SecretStr("synthetic-key"),
        email_from="synthetic@example.test",
        portal_url="https://portal.example.test",
    )
    app = create_app()
    app.dependency_overrides[get_settings] = lambda: settings

    def session():
        with factory() as db:
            yield db

    app.dependency_overrides[get_db] = session
    with TestClient(app) as client:
        yield client, factory, settings
    engine.dispose()


@respx.mock
def test_reset_single_use_expiry_sessions_and_no_enumeration(reset_backend):
    import json

    client, factory, _ = reset_backend
    send = respx.post("https://api.resend.com/emails").mock(
        return_value=httpx.Response(200, json={"id": "x"})
    )
    known = client.post("/auth/password-reset/request", json={"email": "synthetic@example.test"})
    unknown = client.post("/auth/password-reset/request", json={"email": "unknown@example.test"})
    assert known.status_code == unknown.status_code == 202
    assert known.json() == unknown.json()
    text = json.loads(send.calls[0].request.content)["text"]
    token = parse_qs(urlparse(text.split()[1]).query)["token"][0]
    with factory() as db:
        record = db.scalar(select(PasswordResetToken))
        assert record.token_hash != token
    payload = {"token": token, "password": "new-synthetic-password"}
    assert client.post("/auth/password-reset/confirm", json=payload).status_code == 200
    assert client.post("/auth/password-reset/confirm", json=payload).status_code == 400
    with factory() as db:
        assert verify_password(payload["password"], db.scalar(select(User)).password_hash)
        assert db.scalar(select(AuthSession)).revoked_at is not None
    client.post("/auth/password-reset/request", json={"email": "synthetic@example.test"})
    text = json.loads(send.calls[-1].request.content)["text"]
    token = parse_qs(urlparse(text.split()[1]).query)["token"][0]
    with factory() as db:
        record = db.scalar(select(PasswordResetToken).where(PasswordResetToken.used_at.is_(None)))
        record.expires_at = datetime.now(UTC) - timedelta(seconds=1)
        db.commit()
    assert (
        client.post("/auth/password-reset/confirm", json={**payload, "token": token}).status_code
        == 400
    )


@respx.mock
def test_rate_limits_and_provider_failure_are_generic(reset_backend):
    client, _, _ = reset_backend
    send = respx.post("https://api.resend.com/emails").mock(return_value=httpx.Response(500))
    for _ in range(5):
        assert (
            client.post(
                "/auth/password-reset/request", json={"email": "synthetic@example.test"}
            ).status_code
            == 202
        )
    assert send.call_count == 3
    for i in range(25):
        client.post("/auth/password-reset/request", json={"email": f"unknown{i}@example.test"})
    # IP limit prevents another registered-address attempt too.
    assert send.call_count == 3


def test_email_unconfigured(reset_backend, monkeypatch, caplog):
    import logging

    client, _, settings = reset_backend
    settings.resend_api_key = SecretStr("")

    def fail(*args: object, **kwargs: object) -> None:
        raise AssertionError("Resend client must not be called")

    monkeypatch.setattr("app.auth.email.httpx.post", fail)
    with caplog.at_level(logging.INFO, logger="app.auth.email"):
        response = client.post(
            "/auth/password-reset/request", json={"email": "synthetic@example.test"}
        )
        ResendSender(settings, "reset").send(
            email="synthetic@example.test", token="synthetic-token", expires_at=datetime.now(UTC)
        )
    assert response.status_code == 202
    assert "RESEND_API_KEY is not configured" in caplog.text
    assert "synthetic-token" not in caplog.text
    assert "synthetic@example.test" not in caplog.text


@respx.mock
def test_resend_magic_and_invitation_links(reset_backend):
    import json

    _, _, settings = reset_backend
    send = respx.post("https://api.resend.com/emails").mock(return_value=httpx.Response(200))
    for purpose, path in [("magic-link", "sign-in"), ("invitation", "accept-invitation")]:
        ResendSender(settings, purpose).send(
            email="synthetic@example.test", token="synthetic", expires_at=datetime.now(UTC)
        )
        assert f"/{path}?token=synthetic" in json.loads(send.calls[-1].request.content)["text"]


@respx.mock
def test_ip_throttle_applies_across_email_addresses(reset_backend):
    client, factory, _ = reset_backend
    send = respx.post("https://api.resend.com/emails").mock(return_value=httpx.Response(200))
    with factory() as db:
        db.add_all(
            [
                User(email=f"synthetic{i}@example.test", name="Synthetic", role=UserRole.CLIENT)
                for i in range(21)
            ]
        )
        db.commit()
    for i in range(21):
        assert (
            client.post(
                "/auth/password-reset/request", json={"email": f"synthetic{i}@example.test"}
            ).status_code
            == 202
        )
    assert send.call_count == 20


@respx.mock
def test_reset_is_user_bound_and_invalidates_all_other_recovery_links(reset_backend):
    import json

    client, factory, _ = reset_backend
    send = respx.post("https://api.resend.com/emails").mock(return_value=httpx.Response(200))
    with factory() as db:
        db.add(
            User(
                email="other-firm@example.test",
                name="Synthetic Other",
                role=UserRole.CLIENT,
                password_hash=hash_password("other-synthetic-password"),
            )
        )
        db.commit()
    for _ in range(2):
        client.post("/auth/password-reset/request", json={"email": "synthetic@example.test"})
    tokens = [
        parse_qs(urlparse(json.loads(call.request.content)["text"].split()[1]).query)["token"][0]
        for call in send.calls
    ]
    assert (
        client.post(
            "/auth/password-reset/confirm",
            json={"token": tokens[0], "password": "new-synthetic-password"},
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/auth/password-reset/confirm",
            json={"token": tokens[1], "password": "another-synthetic-password"},
        ).status_code
        == 400
    )
    with factory() as db:
        other = db.scalar(select(User).where(User.email == "other-firm@example.test"))
        assert verify_password("other-synthetic-password", other.password_hash)
