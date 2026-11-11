"""Failed sign-in lockout, recovery after the window, and no account enumeration."""

from datetime import UTC, datetime, timedelta

from app.database.models import AuthRateLimit
from tests.test_backend_api import (  # noqa: F401
    AUDITOR_PASSWORD,
    CLIENT_PASSWORD,
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


def test_magic_link_verify_locks_per_token(backend):  # noqa: F811
    client, *_ = backend
    token = "t" * 40
    codes = [
        client.post("/auth/magic-link/verify", json={"token": token}).status_code for _ in range(6)
    ]
    assert codes == [401] * 5 + [429]


def test_one_address_cannot_lock_a_user_out_for_everyone_else(backend):  # noqa: F811
    from starlette.testclient import TestClient

    client, *_ = backend
    for _ in range(5):
        bad(client)  # attacker address
    assert good(client).status_code == 429  # the attacker's own address is locked
    owner = TestClient(client.app, client=("203.0.113.77", 4000))  # the real user, elsewhere
    assert good(owner).status_code == 200


def test_distributed_guessing_hits_the_per_email_ceiling(backend):  # noqa: F811
    from pydantic import SecretStr
    from starlette.testclient import TestClient

    from app.config import Settings, get_settings

    client, *_ = backend
    client.app.dependency_overrides[get_settings] = lambda: Settings(
        _env_file=None,
        session_secret=SecretStr("synthetic-test-session-secret-at-least-32-bytes"),
        signin_max_per_email_total=6,
    )
    codes = []
    for n in range(8):
        other = TestClient(client.app, client=(f"198.51.100.{n + 1}", 4000))
        codes.append(bad(other).status_code)
    assert codes == [401] * 6 + [429] * 2
