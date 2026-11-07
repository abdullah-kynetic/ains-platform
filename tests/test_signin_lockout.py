"""Failed sign-in lockout, recovery after the window, and no account enumeration."""

from datetime import UTC, datetime, timedelta

import pyotp

from app.database.models import AuthRateLimit
from tests.test_backend_api import (  # noqa: F401
    AUDITOR_PASSWORD,
    CLIENT_PASSWORD,
    MFA_SECRET,
    backend,
)


def bad(client, email="alpha-client@example.test"):
    return client.post("/auth/password", json={"email": email, "password": "wrong-password"})


def good(client, email="alpha-client@example.test"):
    return client.post("/auth/password", json={"email": email, "password": CLIENT_PASSWORD})


def test_lockout_after_repeated_failures_blocks_even_the_right_password(backend):  # noqa: F811
    client, *_ = backend
    assert [bad(client).status_code for _ in range(5)] == [401] * 5
    locked = good(client)
    assert locked.status_code == 429
    assert int(locked.headers["Retry-After"]) > 0
    assert "alpha-client" not in locked.text


def test_lockout_recovers_when_the_window_passes(backend):  # noqa: F811
    client, factory, *_ = backend
    for _ in range(5):
        bad(client)
    assert good(client).status_code == 429
    with factory() as db:
        for row in db.query(AuthRateLimit).all():
            row.window_start = datetime.now(UTC) - timedelta(minutes=16)
        db.commit()
    assert good(client).status_code == 200


def test_success_clears_the_email_counter(backend):  # noqa: F811
    client, *_ = backend
    for _ in range(4):
        bad(client)
    assert good(client).status_code == 200
    assert [bad(client).status_code for _ in range(4)] == [401] * 4


def test_unknown_and_known_emails_are_treated_alike(backend):  # noqa: F811
    client, *_ = backend
    codes = [bad(client, "nobody@example.test").status_code for _ in range(6)]
    assert codes == [401] * 5 + [429]


def test_other_accounts_are_not_locked_by_one_email(backend):  # noqa: F811
    client, *_ = backend
    for _ in range(5):
        bad(client)
    assert good(client, "beta-client@example.test").status_code == 200


def test_wrong_mfa_codes_count_as_failures(backend):  # noqa: F811
    client, *_ = backend
    payload = {"email": "auditor@example.test", "password": AUDITOR_PASSWORD, "mfa_code": "000000"}
    assert [client.post("/auth/password", json=payload).status_code for _ in range(5)] == [401] * 5
    payload["mfa_code"] = pyotp.TOTP(MFA_SECRET).now()
    assert client.post("/auth/password", json=payload).status_code == 429


def test_enrollment_endpoints_share_the_password_lockout(backend):  # noqa: F811
    client, *_ = backend
    body = {"email": "enrolling-auditor@example.test", "password": "wrong-password"}
    codes = [client.post("/auth/auditor/mfa/enrollment", json=body).status_code for _ in range(6)]
    assert codes == [401] * 5 + [429]


def test_magic_link_verify_locks_per_token(backend):  # noqa: F811
    client, *_ = backend
    token = "t" * 40
    codes = [
        client.post("/auth/magic-link/verify", json={"token": token}).status_code for _ in range(6)
    ]
    assert codes == [401] * 5 + [429]
