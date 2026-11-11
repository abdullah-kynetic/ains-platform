"""Emailed sign-in codes and remembered browsers (replaces authenticator-app sign-in).

Synthetic users only. Delivery is captured by a fake sender; nothing leaves the process.
"""

import logging
import re
from datetime import UTC, datetime, timedelta

import pytest
from pydantic import SecretStr
from sqlalchemy import select
from starlette.testclient import TestClient

from app.auth.email_code import get_code_sender
from app.config import Settings, get_settings
from app.database.models import (
    AuditLog,
    AuthSession,
    EmailSignInCode,
    Practice,
    TrustedDevice,
    User,
)
from tests.test_backend_api import (
    AUDITOR_PASSWORD,
    CLIENT_PASSWORD,
    backend,  # noqa: F401
)
from tests.test_firm_routes import _auditor

ALPHA = "alpha-client@example.test"
BETA = "beta-client@example.test"
AUDITOR = "auditor@example.test"


class CaptureCodes:
    def __init__(self) -> None:
        self.sent: list[tuple[str, str]] = []

    def send(self, *, email: str, code: str, expires_at: datetime) -> None:
        self.sent.append((email, code))

    @property
    def last(self) -> str:
        return self.sent[-1][1]


def _settings(**over) -> Settings:
    base = dict(
        _env_file=None,
        database_url="sqlite+pysqlite:///:memory:",
        session_secret=SecretStr("synthetic-test-session-secret-at-least-32-bytes"),
        session_cookie_secure=False,
        invitation_preview_enabled=True,
        cors_origins="http://localhost:3000",
        resend_api_key=SecretStr("re_synthetic_not_a_real_key"),
        email_from="Kien <no-reply@example.test>",
        email_code_resend_seconds=0,
    )
    base.update(over)
    return Settings(**base)


@pytest.fixture
def coded(backend):  # noqa: F811
    """The shared backend with emailed codes switched on and a capturing sender."""
    client, factory, ids, *_ = backend
    sender = CaptureCodes()
    client.app.dependency_overrides[get_settings] = lambda: _settings()
    client.app.dependency_overrides[get_code_sender] = lambda: sender
    return client, factory, ids, sender


def _password(client, email=ALPHA, password=CLIENT_PASSWORD, **extra):
    return client.post("/auth/password", json={"email": email, "password": password, **extra})


def _signed_in(client, sender, email=ALPHA, password=CLIENT_PASSWORD, **extra):
    assert _password(client, email, password).status_code == 401
    return _password(client, email, password, code=sender.last, **extra)


def _actions(factory) -> list[str]:
    with factory() as db:
        return [row.action for row in db.scalars(select(AuditLog).order_by(AuditLog.sequence))]


# --- the flow ----------------------------------------------------------------------------


def test_code_is_emailed_after_password_and_signs_in(coded):
    client, factory, ids, sender = coded
    step = _password(client)
    assert step.status_code == 401 and step.json()["detail"] == "Email code required"
    assert "set-cookie" not in step.headers  # no session yet
    assert len(sender.sent) == 1 and sender.sent[0][0] == ALPHA
    assert re.fullmatch(r"\d{6}", sender.last)
    signed = _password(client, code=sender.last)
    assert signed.status_code == 200 and signed.json()["user"]["role"] == "client"
    assert client.get("/auth/session").status_code == 200
    actions = _actions(factory)
    assert "auth.email_code_sent" in actions and "auth.email_code_accepted" in actions


def test_wrong_password_never_sends_a_code(coded):
    client, _, _, sender = coded
    assert _password(client, password="wrong-password-123").status_code == 401
    assert sender.sent == []


def test_auditors_use_the_same_email_code_step(coded):
    client, _, _, sender = coded
    assert _password(client, AUDITOR, AUDITOR_PASSWORD).status_code == 401
    assert sender.sent[0][0] == AUDITOR
    assert _password(client, AUDITOR, AUDITOR_PASSWORD, code=sender.last).status_code == 200
    assert client.get("/auditor/engagements").status_code == 200  # no authenticator needed


def test_code_is_stored_only_as_a_hash(coded):
    client, factory, _, sender = coded
    _password(client)
    with factory() as db:
        row = db.scalar(select(EmailSignInCode))
        assert row.code_hash != sender.last and len(row.code_hash) == 64
    assert sender.last not in str(_actions(factory))


def test_wrong_code_is_rejected_and_audit_logged(coded):
    client, factory, _, sender = coded
    _password(client)
    wrong = "000000" if sender.last != "000000" else "111111"
    denied = _password(client, code=wrong)
    assert denied.status_code == 401 and "set-cookie" not in denied.headers
    assert "auth.email_code_failed" in _actions(factory)
    assert client.get("/auth/session").status_code == 401


def test_code_expires_after_ten_minutes(coded):
    client, factory, _, sender = coded
    _password(client)
    with factory() as db:  # the default window is ten minutes
        row = db.scalar(select(EmailSignInCode))
        window = row.expires_at.replace(tzinfo=UTC) - row.created_at.replace(tzinfo=UTC)
        assert timedelta(minutes=9, seconds=55) < window <= timedelta(minutes=10, seconds=5)
        row.expires_at = datetime.now(UTC) - timedelta(seconds=1)
        db.commit()
    assert _password(client, code=sender.last).status_code == 401
    with factory() as db:
        assert db.scalar(select(EmailSignInCode)).used_at is None


def test_code_works_only_once(coded):
    client, _, _, sender = coded
    assert _signed_in(client, sender).status_code == 200
    first = sender.last
    client.cookies.clear()
    assert _password(client, code=first).status_code == 401  # replay
    assert client.get("/auth/session").status_code == 401


def test_a_new_code_cancels_the_previous_one(coded):
    client, _, _, sender = coded
    _password(client)
    old = sender.last
    resent = client.post(
        "/auth/email-code/resend", json={"email": ALPHA, "password": CLIENT_PASSWORD}
    )
    assert resent.status_code == 202 and len(sender.sent) == 2
    if old != sender.last:
        assert _password(client, code=old).status_code == 401
    # the burned attempt above does not stop the new code
    assert _password(client, code=sender.last).status_code == 200


# --- rate limits -------------------------------------------------------------------------


def test_wrong_guesses_burn_the_code(coded):
    client, _, _, sender = coded
    _password(client)
    right = sender.last
    wrong = "000000" if right != "000000" else "111111"
    assert [_password(client, code=wrong).status_code for _ in range(5)] == [401] * 5
    # Even the correct code is dead after five misses; the sign-in lockout may also apply.
    assert _password(client, code=right).status_code in {401, 429}
    assert client.get("/auth/session").status_code == 401


def test_resend_is_rate_limited(coded):
    client, _, _, sender = coded
    client.app.dependency_overrides[get_settings] = lambda: _settings(
        email_code_max_sends_per_hour=3
    )
    body = {"email": ALPHA, "password": CLIENT_PASSWORD}
    codes = [client.post("/auth/email-code/resend", json=body).status_code for _ in range(4)]
    assert codes == [202, 202, 202, 429]
    assert len(sender.sent) == 3


def test_resend_has_a_cooldown_and_double_submit_sends_one_mail(coded):
    client, _, _, sender = coded
    client.app.dependency_overrides[get_settings] = lambda: _settings(email_code_resend_seconds=60)
    assert _password(client).status_code == 401
    assert _password(client).status_code == 401  # double click: still one email
    assert len(sender.sent) == 1
    body = {"email": ALPHA, "password": CLIENT_PASSWORD}
    again = client.post("/auth/email-code/resend", json=body)
    assert again.status_code == 429 and int(again.headers["retry-after"]) >= 1
    assert len(sender.sent) == 1


def test_resend_needs_the_right_password(coded):
    client, _, _, sender = coded
    body = {"email": ALPHA, "password": "wrong-password-123"}
    assert client.post("/auth/email-code/resend", json=body).status_code == 401
    assert sender.sent == []


def test_email_failure_signs_nobody_in(coded):
    from fastapi import HTTPException

    client, _, _, _ = coded

    class Broken:
        def send(self, **_):
            raise HTTPException(503, "Email delivery unavailable")

    client.app.dependency_overrides[get_code_sender] = lambda: Broken()
    assert _password(client).status_code == 503
    assert client.get("/auth/session").status_code == 401


# --- remembered browsers -----------------------------------------------------------------


def test_remembered_browser_skips_the_code_and_cookie_is_locked_down(coded):
    client, factory, ids, sender = coded
    signed = _signed_in(client, sender, remember_device=True)
    assert signed.status_code == 200
    cookie = next(
        h for h in signed.headers.get_list("set-cookie") if h.startswith("kien_device_")
    ).lower()
    assert "httponly" in cookie and "samesite=lax" in cookie and "max-age=2592000" in cookie
    assert "path=/auth" in cookie
    assert "auth.device_remembered" in _actions(factory)
    sent = len(sender.sent)
    client.cookies.delete("ains_session")
    again = _password(client)  # same browser: no code
    assert again.status_code == 200 and len(sender.sent) == sent


def test_secure_flag_follows_the_cookie_setting(coded):
    client, _, _, sender = coded
    client.app.dependency_overrides[get_settings] = lambda: _settings(session_cookie_secure=True)
    _password(client)
    signed = _password(client, code=sender.last, remember_device=True)
    cookie = next(h for h in signed.headers.get_list("set-cookie") if h.startswith("kien_device_"))
    assert "secure" in cookie.lower()


def test_not_remembered_by_default(coded):
    client, _, _, sender = coded
    signed = _signed_in(client, sender)
    assert not any(h.startswith("kien_device_") for h in signed.headers.get_list("set-cookie"))
    client.cookies.clear()
    assert _password(client).status_code == 401


def test_remembered_browser_stops_working_after_thirty_days(coded):
    client, factory, ids, sender = coded
    _signed_in(client, sender, remember_device=True)
    with factory() as db:
        device = db.scalar(select(TrustedDevice))
        life = device.expires_at.replace(tzinfo=UTC) - device.created_at.replace(tzinfo=UTC)
        assert timedelta(days=29, hours=23) < life <= timedelta(days=30, minutes=1)
        device.expires_at = datetime.now(UTC) - timedelta(seconds=1)  # day 30 has passed
        db.commit()
    client.cookies.delete("ains_session")
    assert _password(client).status_code == 401  # asked for a code again


def test_remembered_browser_belongs_to_one_user_and_firm(coded):
    client, factory, ids, sender = coded
    _signed_in(client, sender, remember_device=True)
    with factory() as db:
        device = db.scalar(select(TrustedDevice))
        token_cookie = {c.name: c.value for c in client.cookies.jar}
        assert device.user_id == ids["client_a"] and device.firm_id == ids["firm_a"]
    # Another firm's user in the same browser is not trusted, even with the cookie copied over.
    from app.auth.email_code import device_cookie_name

    name = next(n for n in token_cookie if n.startswith("kien_device_"))
    client.cookies.clear()
    client.cookies.set(device_cookie_name(ids["client_b"]), token_cookie[name], path="/auth")
    assert _password(client, BETA).status_code == 401
    # The same user with the record re-pointed at another firm is not trusted either.
    with factory() as db:
        db.scalar(select(TrustedDevice)).firm_id = ids["firm_b"]
        db.commit()
    client.cookies.clear()
    client.cookies.set(name, token_cookie[name], path="/auth")
    assert _password(client).status_code == 401


def test_code_for_one_firm_cannot_sign_in_another(coded):
    client, factory, ids, sender = coded
    _password(client)  # code for alpha (firm A)
    alpha_code = sender.last
    other = TestClient(client.app)
    assert _password(other, BETA).status_code == 401
    wrong = alpha_code if alpha_code != sender.last else None
    if wrong:  # beta presenting alpha's code is refused
        assert _password(other, BETA, code=wrong).status_code == 401
    with factory() as db:  # a code row whose firm does not match the user is never accepted
        row = db.scalars(
            select(EmailSignInCode).where(EmailSignInCode.user_id == ids["client_a"])
        ).first()
        row.firm_id = ids["firm_b"]
        db.commit()
    assert _password(client, code=alpha_code).status_code == 401


# --- sign out other devices, admin revoke ------------------------------------------------


def test_user_can_sign_out_other_devices(coded):
    client, factory, ids, sender = coded
    _signed_in(client, sender, remember_device=True)
    laptop = TestClient(client.app)
    assert _signed_in(laptop, sender, remember_device=True).status_code == 200
    assert laptop.get("/auth/session").status_code == 200
    assert client.get("/auth/session").status_code == 200
    ended = client.post("/auth/sign-out-others")
    assert ended.status_code == 200 and ended.json() == {
        "sessions_ended": 1,
        "devices_forgotten": 1,
    }
    assert laptop.get("/auth/session").status_code == 401  # the other device is out
    assert client.get("/auth/session").status_code == 200  # this one stays
    laptop.cookies.delete("ains_session")
    assert _password(laptop).status_code == 401  # and must use a code again
    client.cookies.delete("ains_session")
    assert _password(client).status_code == 200  # this browser is still remembered
    assert "auth.device_revoked" in _actions(factory)


def test_sign_out_others_needs_a_session(coded):
    client, *_ = coded
    assert client.post("/auth/sign-out-others").status_code == 401


def test_password_reset_forgets_remembered_browsers(coded):
    from app.auth.email_code import revoke_devices

    client, factory, ids, sender = coded
    _signed_in(client, sender, remember_device=True)
    with factory() as db:
        user = db.get(User, ids["client_a"])
        assert revoke_devices(db, user, actor=user, reason="password_reset") == 1
        db.commit()
    client.cookies.delete("ains_session")
    assert _password(client).status_code == 401


def _admin_world(coded):
    client, factory, ids, sender = coded
    with factory() as db:
        a = Practice(name="Synthetic Practice A")
        b = Practice(name="Synthetic Practice B")
        db.add_all([a, b])
        db.flush()
        partner = db.get(User, ids["auditor"])
        partner.practice_id, partner.team_role = a.id, "partner"
        member = _auditor(db, "plain-a@example.test", a.id, "auditor")
        _auditor(db, "partner-b@example.test", b.id, "partner")
        db.commit()
        ids = {**ids, "member": member.id}
    return client, factory, ids, sender


def _remembered(client, sender, email, password) -> TestClient:
    browser = TestClient(client.app)
    assert _signed_in(browser, sender, email, password, remember_device=True).status_code == 200
    return browser


def test_partner_revokes_a_team_members_devices(coded):
    client, factory, ids, sender = _admin_world(coded)
    member = _remembered(client, sender, "plain-a@example.test", AUDITOR_PASSWORD)
    partner = _remembered(client, sender, AUDITOR, AUDITOR_PASSWORD)
    done = partner.post(f"/auditor/firm/team/{ids['member']}/devices/revoke")
    assert done.status_code == 200 and done.json() == {"devices_forgotten": 1}
    member.cookies.delete("ains_session")
    assert _password(member, "plain-a@example.test", AUDITOR_PASSWORD).status_code == 401
    with factory() as db:
        revoked = db.scalars(select(AuditLog).where(AuditLog.action == "auth.device_revoked")).all()
        assert revoked and revoked[-1].actor_id == ids["auditor"]
        assert revoked[-1].entity_id == ids["member"]


def test_only_partners_or_admins_revoke_and_only_inside_their_practice(coded):
    client, factory, ids, sender = _admin_world(coded)
    _remembered(client, sender, ALPHA, CLIENT_PASSWORD)
    member = f"/auditor/firm/team/{ids['member']}/devices/revoke"
    alpha = f"/auditor/firm/clients/{ids['client_a']}/devices/revoke"
    # a plain auditor (not partner/admin)
    plain = TestClient(client.app)
    assert _signed_in(plain, sender, "plain-a@example.test", AUDITOR_PASSWORD).status_code == 200
    assert plain.post(alpha).status_code == 403 and plain.post(member).status_code == 403
    # a client is denied
    assert _password(plain, ALPHA, CLIENT_PASSWORD).status_code in {200, 401}
    client_session = TestClient(client.app)
    assert _signed_in(client_session, sender, ALPHA, CLIENT_PASSWORD).status_code == 200
    assert client_session.post(member).status_code == 403
    # a partner of an unrelated practice cannot reach either target (cross-tenant denial)
    other = TestClient(client.app)
    assert _signed_in(other, sender, "partner-b@example.test", AUDITOR_PASSWORD).status_code == 200
    assert other.post(member).status_code == 404
    assert other.post(alpha).status_code == 404
    with factory() as db:
        assert db.scalar(select(TrustedDevice).where(TrustedDevice.revoked_at.is_not(None))) is None


def test_partner_revokes_a_client_devices_for_an_assigned_firm(coded):
    client, factory, ids, sender = _admin_world(coded)
    alpha = _remembered(client, sender, ALPHA, CLIENT_PASSWORD)
    partner = _remembered(client, sender, AUDITOR, AUDITOR_PASSWORD)
    done = partner.post(f"/auditor/firm/clients/{ids['client_a']}/devices/revoke")
    assert done.status_code == 200 and done.json() == {"devices_forgotten": 1}
    alpha.cookies.delete("ains_session")
    assert _password(alpha).status_code == 401
    # an auditor id is not a client id
    assert partner.post(f"/auditor/firm/clients/{ids['member']}/devices/revoke").status_code == 404


# --- fallback with no email key ----------------------------------------------------------


def test_without_an_email_key_sign_in_is_password_only_with_a_log_note(backend, caplog):  # noqa: F811
    client, factory, ids, *_ = backend  # the shared fixture has no RESEND_API_KEY
    with caplog.at_level(logging.WARNING, logger="app.auth.email_code"):
        signed = _password(client)
    assert signed.status_code == 200
    assert "Email sign-in codes are OFF" in caplog.text
    assert "RESEND_API_KEY" in caplog.text and CLIENT_PASSWORD not in caplog.text
    with factory() as db:
        assert db.scalar(select(EmailSignInCode)) is None


def test_flag_off_forces_password_only_even_with_a_key(coded, caplog):
    client, _, _, sender = coded
    client.app.dependency_overrides[get_settings] = lambda: _settings(email_sign_in_codes=False)
    assert _password(client).status_code == 200
    assert sender.sent == []
    assert (
        client.post(
            "/auth/email-code/resend", json={"email": ALPHA, "password": CLIENT_PASSWORD}
        ).status_code
        == 404
    )


def test_capabilities_report_the_email_code_step(coded, backend):  # noqa: F811
    client, *_ = coded
    assert client.get("/auth/capabilities").json()["email_code"] is True
    client.app.dependency_overrides[get_settings] = lambda: _settings(resend_api_key=SecretStr(""))
    assert client.get("/auth/capabilities").json()["email_code"] is False


def test_a_signed_in_session_is_not_blocked_by_missing_authenticator(coded):
    client, factory, ids, sender = coded
    _signed_in(client, sender, AUDITOR, AUDITOR_PASSWORD)
    with factory() as db:
        assert db.get(User, ids["auditor"]).mfa_enabled is False
        assert db.scalar(select(AuthSession)) is not None
    assert client.get("/auth/session").status_code == 200
