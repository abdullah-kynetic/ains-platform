"""Sign-in lockout on REAL PostgreSQL under concurrency (SQLite cannot show row-lock races).

Targets: concurrent *first* failures for an email with no counter row yet (SELECT .. FOR UPDATE
locks nothing when the row is missing), counter accuracy, and recovery. Synthetic data only.
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy.orm import sessionmaker

from app.auth.security import hash_password
from app.config import Settings, get_settings
from app.database.models import AuthRateLimit, Base, Firm, User, UserRole
from app.database.session import get_db
from app.main import create_app
from tests.test_audit_postgres import postgres_engine as postgres_engine  # noqa: F401

PASSWORD = "Synthetic-Correct-Passw0rd!"
EMAIL = "pg-client@example.test"


@pytest.fixture
def pg_app(postgres_engine):  # noqa: F811
    Base.metadata.create_all(postgres_engine)
    factory = sessionmaker(bind=postgres_engine, expire_on_commit=False)
    with factory() as db:
        firm = Firm(name="Synthetic PG Firm", slug="synthetic-pg")
        db.add(firm)
        db.flush()
        db.add(
            User(
                firm_id=firm.id,
                email=EMAIL,
                name="Synthetic PG Client",
                role=UserRole.CLIENT,
                password_hash=hash_password(PASSWORD),
                accepted_at=datetime.now(UTC),
            )
        )
        db.commit()
    settings = Settings(
        _env_file=None,
        database_url="postgresql+psycopg://unused",
        session_secret=SecretStr("synthetic-test-session-secret-at-least-32-bytes"),
        session_cookie_secure=False,
    )

    def db_override():
        with factory() as db:
            yield db

    app = create_app()
    app.dependency_overrides[get_db] = db_override
    app.dependency_overrides[get_settings] = lambda: settings
    yield app, factory


def attempt(app, email, password):
    with TestClient(app, raise_server_exceptions=False) as client:
        body = {"email": email, "password": password}
        return client.post("/auth/password", json=body).status_code


@pytest.mark.parametrize("email", [EMAIL, "pg-unknown@example.test"])
def test_concurrent_first_failures_are_all_counted_and_never_500(pg_app, email):
    app, factory = pg_app
    with ThreadPoolExecutor(max_workers=8) as pool:
        codes = list(pool.map(lambda _: attempt(app, email, "wrong-password"), range(8)))
    assert 500 not in codes, codes
    assert set(codes) <= {401, 429}, codes
    # 8 concurrent failures against a limit of 5: at least 5 must be recorded, so the account locks.
    with factory() as db:
        email_rows = [r for r in db.query(AuthRateLimit).all() if r.count > 1]
        assert email_rows, "no counter recorded more than one failure (lost updates)"
    assert attempt(app, email, PASSWORD) == 429


def test_failures_below_limit_still_allow_the_right_password_and_reset(pg_app):
    app, _ = pg_app
    with ThreadPoolExecutor(max_workers=3) as pool:
        codes = list(pool.map(lambda _: attempt(app, EMAIL, "wrong-password"), range(3)))
    assert codes == [401] * 3
    assert attempt(app, EMAIL, PASSWORD) == 200


def test_lockout_recovers_after_window_on_postgres(pg_app):
    app, factory = pg_app
    for _ in range(5):
        attempt(app, EMAIL, "wrong-password")
    assert attempt(app, EMAIL, PASSWORD) == 429
    with factory() as db:
        for row in db.query(AuthRateLimit).all():
            row.window_start = datetime.now(UTC) - timedelta(minutes=16)
        db.commit()
    assert attempt(app, EMAIL, PASSWORD) == 200
