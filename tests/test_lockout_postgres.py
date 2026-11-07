"""Lockout counters on real PostgreSQL: concurrent first failures must not error or lose counts.

Run as a non-root user (initdb refuses root); see tests/run_as_nonroot.sh or the bundle README.
"""

import threading
from datetime import UTC, datetime
from types import SimpleNamespace

from sqlalchemy.orm import Session

from app.auth.lockout import SignInGuard
from app.config import Settings
from app.database.models import AuthRateLimit
from tests.test_audit_postgres import postgres_engine  # noqa: F401


def _guard(db, ip="198.51.100.9"):
    request = SimpleNamespace(client=SimpleNamespace(host=ip))
    return SignInGuard(db, request, Settings(_env_file=None), "signin", "racer@example.test")


def test_concurrent_first_failures_are_counted_exactly_once_each(postgres_engine):  # noqa: F811
    AuthRateLimit.__table__.create(postgres_engine, checkfirst=True)
    threads, errors = 8, []
    barrier = threading.Barrier(threads)

    def worker():
        try:
            with Session(postgres_engine) as db:
                guard = _guard(db)
                barrier.wait()
                guard.fail()
        except Exception as exc:  # noqa: BLE001 - the test reports any failure
            errors.append(repr(exc))

    pool = [threading.Thread(target=worker) for _ in range(threads)]
    for t in pool:
        t.start()
    for t in pool:
        t.join()
    assert errors == []
    with Session(postgres_engine) as db:
        rows = {r.key: r.count for r in db.query(AuthRateLimit)}
        assert rows and set(rows.values()) == {threads}  # all three keys saw all 8 failures


def test_lock_and_recovery_on_postgres(postgres_engine):  # noqa: F811
    AuthRateLimit.__table__.create(postgres_engine, checkfirst=True)
    with Session(postgres_engine) as db:
        for _ in range(5):
            _guard(db, "198.51.100.50").fail()
        try:
            _guard(db, "198.51.100.50").check()
            raise AssertionError("expected a lock")
        except Exception as exc:  # noqa: BLE001
            assert getattr(exc, "status_code", None) == 429
        for row in db.query(AuthRateLimit):
            row.window_start = datetime(2020, 1, 1, tzinfo=UTC)
        db.commit()
        _guard(db, "198.51.100.50").check()  # window passed: allowed again
