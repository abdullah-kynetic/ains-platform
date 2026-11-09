"""Failed-attempt lockout for sign-in. Counters live in auth_rate_limits (shared across workers).

Keyed by normalised email (whether or not the account exists, so responses do not reveal
accounts) and by client address. A locked client gets 429 with Retry-After and recovers when the
window passes; a successful sign-in clears the email counter.
"""

import hashlib
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, Request
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from app.config import Settings
from app.database.models import AuthRateLimit

_INSERTS = {"postgresql": pg_insert, "sqlite": sqlite_insert}


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=UTC)


class SignInGuard:
    def __init__(
        self, db: Session, request: Request, settings: Settings, scope: str, email: str
    ) -> None:
        ip = request.client.host if request.client else "unknown"
        self.db = db
        self.window = timedelta(minutes=settings.signin_lockout_minutes)
        email = email.strip().casefold()
        # The pair key means one address cannot lock a user out for everyone else; the softer
        # per-email ceiling and the per-address limit still bound distributed guessing.
        self.limits = [
            (self._key(f"{scope}-pair", f"{email}|{ip}"), settings.signin_max_per_email),
            (self._key(f"{scope}-email", email), settings.signin_max_per_email_total),
            (self._key(f"{scope}-ip", ip), settings.signin_max_per_ip),
        ]

    @staticmethod
    def _key(kind: str, identity: str) -> str:
        return hashlib.sha256(f"{kind}:{identity}".encode()).hexdigest()

    def _row(self, key: str, now: datetime, create: bool) -> AuthRateLimit | None:
        if create:
            # Race-safe first insert: concurrent first failures cannot raise an integrity error.
            dialect = self.db.get_bind().dialect.name
            insert = _INSERTS.get(dialect)
            if insert is not None:
                self.db.execute(
                    insert(AuthRateLimit)
                    .values(key=key, count=0, window_start=now)
                    .on_conflict_do_nothing(index_elements=["key"])
                )
        row = self.db.get(AuthRateLimit, key, with_for_update=True)
        if row is not None and _aware(row.window_start) + self.window <= now:
            row.count, row.window_start = 0, now  # window passed: recovered
        if row is None and create:  # dialects without ON CONFLICT support
            row = AuthRateLimit(key=key, count=0, window_start=now)
            self.db.add(row)
        return row

    def check(self) -> None:
        now = datetime.now(UTC)
        for key, limit in self.limits:
            row = self._row(key, now, create=False)
            if row is not None and row.count >= limit:
                wait = int((_aware(row.window_start) + self.window - now).total_seconds()) + 1
                self.db.commit()
                raise HTTPException(
                    status_code=429,
                    detail="Too many failed attempts. Try again later.",
                    headers={"Retry-After": str(max(wait, 1))},
                )
        self.db.commit()

    def fail(self) -> None:
        now = datetime.now(UTC)
        for key, _ in self.limits:
            self._row(key, now, create=True).count += 1
        self.db.commit()

    def succeed(self) -> None:
        row = self.db.get(AuthRateLimit, self.limits[0][0], with_for_update=True)
        if row is not None:
            row.count = 0
        self.db.commit()
