"""Synthetic Resend delivery. HTTP is mocked; no provider calls or real addresses."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime

import httpx
import pytest
import respx
from fastapi import HTTPException
from pydantic import SecretStr
from sqlalchemy import select

from app.auth.email import (
    BRAND_NAME,
    EMAIL_FROM,
    RESEND_EMAILS_URL,
    ResendSender,
    notify_report_ready,
)
from app.config import Settings, get_settings
from app.database.models import ClientInvitation, Engagement, EngagementStatus, User, UserRole
from tests.test_backend_api import backend, sign_in_auditor  # noqa: F401

EXPIRES = datetime(2026, 1, 2, 3, 4, tzinfo=UTC)
API_KEY = "re_synthetic_test_key"


def _settings(key: str = API_KEY) -> Settings:
    return Settings(
        _env_file=None,
        resend_api_key=SecretStr(key),
        portal_url="https://portal.example.test",
    )


def _payload(call: httpx.Request) -> dict[str, object]:
    body = json.loads(call.content)
    assert isinstance(body, dict)
    return body


@pytest.mark.parametrize(
    ("purpose", "path", "subject"),
    [
        ("invitation", "accept-invitation", "You're invited to Kien Solutions"),
        ("reset", "reset-password", "Reset your Kien Solutions password"),
    ],
)
@respx.mock
def test_invite_and_reset_send_branded_messages(purpose: str, path: str, subject: str) -> None:
    route = respx.post(RESEND_EMAILS_URL).mock(
        return_value=httpx.Response(200, json={"id": "synthetic-email"})
    )
    ResendSender(_settings(), purpose).send(
        email="synthetic@example.test", token="synthetic-token", expires_at=EXPIRES
    )
    assert route.call_count == 1
    sent = _payload(route.calls[0].request)
    assert sent["from"] == EMAIL_FROM
    assert sent["from"] == "Kien Solutions <no-reply@kiensolutions.com>"
    assert sent["to"] == ["synthetic@example.test"]
    assert sent["subject"] == subject
    assert BRAND_NAME in str(sent["text"])
    assert BRAND_NAME in str(sent["html"])
    assert f"/{path}?token=synthetic-token" in str(sent["text"])
    assert route.calls[0].request.headers["authorization"] == f"Bearer {API_KEY}"
    assert API_KEY not in route.calls[0].request.content.decode()


@respx.mock
def test_report_ready_send_omits_findings() -> None:
    route = respx.post(RESEND_EMAILS_URL).mock(
        return_value=httpx.Response(200, json={"id": "synthetic-email"})
    )
    ResendSender(_settings(), "report-ready").send_report_ready(
        email="synthetic@example.test",
        firm_name="Synthetic Alpha Securities",
        review_period="2025-01-01 through 2025-12-31",
    )
    sent = _payload(route.calls[0].request)
    text = str(sent["text"])
    assert sent["from"] == EMAIL_FROM
    assert sent["subject"] == "Your Kien Solutions report is ready"
    assert "Synthetic Alpha Securities" in text
    assert "2025-01-01 through 2025-12-31" in text
    assert "https://portal.example.test" in text
    assert "finding" not in text.casefold()
    assert "sar" not in text.casefold()
    assert "citation" not in text.casefold()
    assert BRAND_NAME in str(sent["html"])


@pytest.mark.parametrize("purpose", ["invitation", "reset"])
def test_missing_key_skips_link_mail_without_calling_resend(
    purpose: str, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    def fail(*args: object, **kwargs: object) -> None:
        raise AssertionError("Resend client must not be called")

    monkeypatch.setattr("app.auth.email.httpx.post", fail)
    with caplog.at_level(logging.INFO, logger="app.auth.email"):
        ResendSender(_settings(key="  "), purpose).send(
            email="synthetic@example.test", token="synthetic-token", expires_at=EXPIRES
        )
    messages = [record.getMessage() for record in caplog.records if record.name == "app.auth.email"]
    assert any("RESEND_API_KEY is not configured" in message for message in messages)
    assert all("synthetic@example.test" not in message for message in messages)
    assert all("synthetic-token" not in message for message in messages)


def test_missing_key_skips_report_ready_without_calling_resend(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    def fail(*args: object, **kwargs: object) -> None:
        raise AssertionError("Resend client must not be called")

    monkeypatch.setattr("app.auth.email.httpx.post", fail)
    with caplog.at_level(logging.INFO, logger="app.auth.email"):
        notify_report_ready(
            _settings(key=""),
            recipients=["synthetic@example.test"],
            firm_name="Synthetic Alpha Securities",
            review_period="2025-01-01 through 2025-12-31",
        )
    assert "RESEND_API_KEY is not configured" in caplog.text
    assert "synthetic@example.test" not in caplog.text
    assert "Synthetic Alpha Securities" not in caplog.text


@respx.mock
def test_provider_failure_is_generic_and_does_not_log_the_body(
    caplog: pytest.LogCaptureFixture,
) -> None:
    respx.post(RESEND_EMAILS_URL).mock(
        return_value=httpx.Response(502, json={"message": "provider-secret-body"})
    )
    with caplog.at_level(logging.WARNING, logger="app.auth.email"):
        with pytest.raises(HTTPException) as caught:
            ResendSender(_settings(), "invitation").send(
                email="synthetic@example.test", token="synthetic-token", expires_at=EXPIRES
            )
    assert caught.value.status_code == 503
    assert caught.value.detail == "Email delivery unavailable"
    assert "provider-secret-body" not in caplog.text
    assert API_KEY not in caplog.text
    assert "synthetic-token" not in caplog.text


@respx.mock
def test_report_ready_delivery_continues_when_one_recipient_fails(
    caplog: pytest.LogCaptureFixture,
) -> None:
    route = respx.post(RESEND_EMAILS_URL).mock(
        side_effect=[
            httpx.Response(200, json={"id": "synthetic-email"}),
            httpx.Response(502, json={"message": "provider-secret-body"}),
        ]
    )
    with caplog.at_level(logging.WARNING, logger="app.auth.email"):
        notify_report_ready(
            _settings(),
            recipients=["first@example.test", "second@example.test"],
            firm_name="Synthetic Alpha Securities",
            review_period="2025-01-01 through 2025-12-31",
        )
    assert route.call_count == 2
    assert "provider-secret-body" not in caplog.text
    assert "report-ready email was not delivered" in caplog.text


@respx.mock
def test_configured_invitation_posts_to_resend(backend) -> None:  # noqa: F811
    client, _, ids, _, _ = backend
    settings = client.app.dependency_overrides[get_settings]()
    client.app.dependency_overrides[get_settings] = lambda: settings.model_copy(
        update={
            "invitation_preview_enabled": False,
            "resend_api_key": SecretStr(API_KEY),
            "portal_url": "https://portal.example.test",
        }
    )
    route = respx.post(RESEND_EMAILS_URL).mock(
        return_value=httpx.Response(200, json={"id": "synthetic-email"})
    )
    sign_in_auditor(client)
    created = client.post(
        f"/auditor/engagements/{ids['engagement_a']}/invitations",
        json={"email": "invited-client@example.test", "name": "Synthetic Invited Client"},
    )
    assert created.status_code == 201
    sent = _payload(route.calls[0].request)
    assert sent["to"] == ["invited-client@example.test"]
    assert sent["from"] == EMAIL_FROM
    assert "accept-invitation?token=" in str(sent["text"])
    assert BRAND_NAME in str(sent["subject"])


@respx.mock
def test_invitation_provider_failure_does_not_persist(backend) -> None:  # noqa: F811
    client, factory, ids, _, _ = backend
    settings = client.app.dependency_overrides[get_settings]()
    client.app.dependency_overrides[get_settings] = lambda: settings.model_copy(
        update={"invitation_preview_enabled": False, "resend_api_key": SecretStr(API_KEY)}
    )
    respx.post(RESEND_EMAILS_URL).mock(
        return_value=httpx.Response(500, json={"message": "provider-secret-body"})
    )
    sign_in_auditor(client)
    response = client.post(
        f"/auditor/engagements/{ids['engagement_a']}/invitations",
        json={"email": "undelivered-client@example.test", "name": "Synthetic Undelivered"},
    )
    assert response.status_code == 503
    assert response.json()["detail"] == "Email delivery unavailable"
    assert "provider-secret-body" not in response.text
    with factory() as db:
        assert (
            db.scalar(
                select(ClientInvitation).where(
                    ClientInvitation.email == "undelivered-client@example.test"
                )
            )
            is None
        )


@respx.mock
def test_signoff_emails_only_active_clients_of_that_firm(backend) -> None:  # noqa: F811
    client, factory, ids, _, _ = backend
    settings = client.app.dependency_overrides[get_settings]()
    client.app.dependency_overrides[get_settings] = lambda: settings.model_copy(
        update={"resend_api_key": SecretStr(API_KEY), "portal_url": "https://portal.example.test"}
    )
    route = respx.post(RESEND_EMAILS_URL).mock(
        return_value=httpx.Response(200, json={"id": "synthetic-email"})
    )
    with factory() as db:
        db.add(
            User(
                firm_id=ids["firm_a"],
                email="inactive-client@example.test",
                name="Synthetic Inactive Client",
                role=UserRole.CLIENT,
                is_active=False,
            )
        )
        db.get(Engagement, ids["engagement_a"]).status = EngagementStatus.AWAITING_SIGNATURE
        db.commit()
    sign_in_auditor(client)
    digest = "ab" * 32
    response = client.post(
        f"/auditor/engagements/{ids['engagement_a']}/report/signoff",
        json={"reportSha256": digest, "attestation": True},
    )
    assert response.status_code == 200
    assert route.call_count == 1
    sent = _payload(route.calls[0].request)
    assert sent["to"] == ["alpha-client@example.test"]
    assert sent["from"] == EMAIL_FROM
    assert sent["subject"] == "Your Kien Solutions report is ready"
    assert "Synthetic Alpha Securities" in str(sent["text"])
    assert digest not in str(sent["text"])
    assert "finding" not in str(sent["text"]).casefold()
    assert "beta-client@example.test" not in str(sent["to"])


def test_signoff_without_key_still_completes(
    backend,  # noqa: F811
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail(*args: object, **kwargs: object) -> None:
        raise AssertionError("Resend client must not be called")

    monkeypatch.setattr("app.auth.email.httpx.post", fail)
    client, factory, ids, _, _ = backend
    with factory() as db:
        db.get(Engagement, ids["engagement_a"]).status = EngagementStatus.AWAITING_SIGNATURE
        db.commit()
    sign_in_auditor(client)
    response = client.post(
        f"/auditor/engagements/{ids['engagement_a']}/report/signoff",
        json={"reportSha256": "cd" * 32, "attestation": True},
    )
    assert response.status_code == 200
    assert response.json()["signed_off"] is True
