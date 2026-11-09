"""Report-ready email. Synthetic data only; Resend HTTP is mocked, nothing is sent."""

from __future__ import annotations

import json
import logging

import httpx
import pytest
import respx
from pydantic import SecretStr

from app.auth.email import notify_report_ready
from app.config import Settings, get_settings
from app.database.models import Engagement, EngagementStatus, User, UserRole
from tests.test_backend_api import backend, sign_in_auditor  # noqa: F401

RESEND_URL = "https://api.resend.com/emails"
API_KEY = "re_synthetic_test_key"
FROM = "Kien <no-reply@example.test>"
PERIOD = "2025-01-01 through 2025-12-31"


@pytest.fixture(autouse=True)
def enable_email_log_capture(monkeypatch: pytest.MonkeyPatch) -> None:
    # Earlier migration tests run Alembic fileConfig in this process and disable
    # existing loggers. Real migrations run separately from the API; isolate that
    # test-only global state so privacy assertions still inspect emitted records.
    monkeypatch.setattr(logging.getLogger("app.auth.email"), "disabled", False)


def _settings(key: str = API_KEY, email_from: str = FROM) -> Settings:
    return Settings(
        _env_file=None,
        resend_api_key=SecretStr(key),
        email_from=email_from,
        portal_url="https://portal.example.test",
    )


def _no_http(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(*args: object, **kwargs: object) -> None:
        raise AssertionError("Resend must not be called")

    monkeypatch.setattr("app.auth.email.httpx.post", fail)


@respx.mock
def test_report_ready_payload_has_no_findings() -> None:
    route = respx.post(RESEND_URL).mock(return_value=httpx.Response(200, json={"id": "x"}))
    notify_report_ready(
        _settings(),
        recipients=["synthetic@example.test"],
        firm_name="Synthetic Alpha Securities",
        review_period=PERIOD,
    )
    sent = json.loads(route.calls[0].request.content)
    text = sent["text"].casefold()
    assert sent["from"] == FROM
    assert sent["to"] == ["synthetic@example.test"]
    assert "synthetic alpha securities" in text and "2025-12-31" in text
    assert "https://portal.example.test" in text
    assert "finding" not in text.replace("does not include", "")
    assert route.calls[0].request.headers["authorization"] == f"Bearer {API_KEY}"


@pytest.mark.parametrize("key,sender", [("", FROM), ("  ", FROM), (API_KEY, "")])
def test_unconfigured_skips_without_calling_resend(
    key: str, sender: str, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    _no_http(monkeypatch)
    with caplog.at_level(logging.INFO, logger="app.auth.email"):
        notify_report_ready(
            _settings(key=key, email_from=sender),
            recipients=["synthetic@example.test"],
            firm_name="Synthetic Alpha Securities",
            review_period=PERIOD,
        )
    assert "skipped" in caplog.text
    assert "synthetic@example.test" not in caplog.text


@respx.mock
def test_one_failed_recipient_does_not_stop_the_rest(caplog: pytest.LogCaptureFixture) -> None:
    route = respx.post(RESEND_URL).mock(
        side_effect=[
            httpx.Response(502, json={"message": "provider-secret-body"}),
            httpx.Response(200, json={"id": "x"}),
        ]
    )
    with caplog.at_level(logging.WARNING, logger="app.auth.email"):
        notify_report_ready(
            _settings(),
            recipients=["a@example.test", "b@example.test"],
            firm_name="Synthetic Alpha Securities",
            review_period=PERIOD,
        )
    assert route.call_count == 2
    assert "not delivered" in caplog.text
    assert "provider-secret-body" not in caplog.text
    assert API_KEY not in caplog.text
    assert "a@example.test" not in caplog.text


@respx.mock
def test_signoff_emails_only_active_clients_of_that_firm(backend) -> None:  # noqa: F811
    client, factory, ids, _, _ = backend
    base = client.app.dependency_overrides[get_settings]()
    client.app.dependency_overrides[get_settings] = lambda: base.model_copy(
        update={"resend_api_key": SecretStr(API_KEY), "email_from": FROM}
    )
    route = respx.post(RESEND_URL).mock(return_value=httpx.Response(200, json={"id": "x"}))
    with factory() as db:
        db.add(
            User(
                firm_id=ids["firm_a"],
                email="inactive-client@example.test",
                name="Synthetic Inactive",
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
    sent = json.loads(route.calls[0].request.content)
    assert sent["to"] == ["alpha-client@example.test"]
    assert digest not in sent["text"]
    assert "Synthetic Alpha Securities" in sent["text"]


@respx.mock
def test_signoff_succeeds_even_if_provider_fails(backend) -> None:  # noqa: F811
    client, factory, ids, _, _ = backend
    base = client.app.dependency_overrides[get_settings]()
    client.app.dependency_overrides[get_settings] = lambda: base.model_copy(
        update={"resend_api_key": SecretStr(API_KEY), "email_from": FROM}
    )
    respx.post(RESEND_URL).mock(return_value=httpx.Response(500))
    with factory() as db:
        db.get(Engagement, ids["engagement_a"]).status = EngagementStatus.AWAITING_SIGNATURE
        db.commit()
    sign_in_auditor(client)
    response = client.post(
        f"/auditor/engagements/{ids['engagement_a']}/report/signoff",
        json={"reportSha256": "cd" * 32, "attestation": True},
    )
    assert response.status_code == 200 and response.json()["signed_off"] is True
    with factory() as db:
        assert db.get(Engagement, ids["engagement_a"]).status == EngagementStatus.COMPLETE


def test_signoff_without_key_still_completes(backend, monkeypatch) -> None:  # noqa: F811
    _no_http(monkeypatch)
    client, factory, ids, _, _ = backend
    base = client.app.dependency_overrides[get_settings]()
    client.app.dependency_overrides[get_settings] = lambda: base.model_copy(
        update={"resend_api_key": SecretStr(""), "email_from": ""}
    )
    with factory() as db:
        db.get(Engagement, ids["engagement_a"]).status = EngagementStatus.AWAITING_SIGNATURE
        db.commit()
    sign_in_auditor(client)
    response = client.post(
        f"/auditor/engagements/{ids['engagement_a']}/report/signoff",
        json={"reportSha256": "ef" * 32, "attestation": True},
    )
    assert response.status_code == 200


def test_unexpected_error_is_swallowed(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    def boom(*args: object, **kwargs: object) -> None:
        raise ValueError("synthetic@example.test provider-secret-body")

    monkeypatch.setattr("app.auth.email.httpx.post", boom)
    notify_report_ready(
        _settings(),
        recipients=["synthetic@example.test"],
        firm_name="Synthetic Alpha Securities",
        review_period=PERIOD,
    )
    assert "ValueError" in caplog.text
    assert "synthetic@example.test" not in caplog.text
    assert "provider-secret-body" not in caplog.text
    assert API_KEY not in caplog.text
