"""Durable counters for the adapter: daily request cap and consecutive errors."""

from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import (
    Column,
    DateTime,
    Integer,
    MetaData,
    String,
    Table,
    create_engine,
    select,
    text,
)
from sqlalchemy.engine import make_url

_meta = MetaData()
counters = Table(
    "ai_counters", _meta, Column("key", String(80), primary_key=True), Column("value", Integer)
)
# Durable record of every AI call attempt, firm-scoped. Holds identifiers and outcomes only:
# never document text, prompts, model output or secrets.
call_log = Table(
    "ai_call_log",
    _meta,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("at", DateTime(timezone=True), nullable=False),
    Column("firm_id", String(64), nullable=False, index=True),
    Column("engagement_id", String(64), nullable=False),
    Column("user_id", String(64), nullable=False),
    Column("document_id", String(64), nullable=False),
    Column("item_id", String(40), nullable=False),
    Column("model", String(120), nullable=False),
    Column("prompt_version", String(20), nullable=False),
    Column("outcome", String(20), nullable=False),  # ok | refused | error
    Column("code", String(60), nullable=False, default=""),
    Column("prompt_tokens", Integer),
    Column("completion_tokens", Integer),
)


class StateStore:
    def __init__(self, url: str) -> None:
        parsed = make_url(url)
        if parsed.get_backend_name() == "sqlite" and parsed.database not in (None, ":memory:"):
            Path(parsed.database).parent.mkdir(parents=True, exist_ok=True)
        self.engine = create_engine(url)
        _meta.create_all(self.engine)

    def _ensure(self, conn, key: str) -> None:
        conn.execute(
            text(
                "INSERT INTO ai_counters (key, value) VALUES (:k, 0) ON CONFLICT (key) DO NOTHING"
            ),
            {"k": key},
        )

    def take_daily(self, cap: int) -> bool:
        """Atomically consume one request from today's cap; False when the cap is reached."""
        key = f"daily:{datetime.now(UTC):%Y-%m-%d}"
        with self.engine.begin() as conn:
            self._ensure(conn, key)
            result = conn.execute(
                text("UPDATE ai_counters SET value = value + 1 WHERE key = :k AND value < :cap"),
                {"k": key, "cap": cap},
            )
            return result.rowcount == 1

    def add_error(self) -> int:
        with self.engine.begin() as conn:
            self._ensure(conn, "errors")
            conn.execute(text("UPDATE ai_counters SET value = value + 1 WHERE key = 'errors'"))
            return conn.execute(text("SELECT value FROM ai_counters WHERE key = 'errors'")).scalar()

    def clear_errors(self) -> None:
        with self.engine.begin() as conn:
            conn.execute(text("UPDATE ai_counters SET value = 0 WHERE key = 'errors'"))

    def log_call(self, **fields) -> None:
        with self.engine.begin() as conn:
            conn.execute(call_log.insert().values(at=datetime.now(UTC), **fields))

    def calls_for_firm(self, firm_id: str, engagement_id: str | None = None) -> list[dict]:
        """Read back log rows for one firm (and optionally one engagement). Never crosses firms."""
        query = select(call_log).where(call_log.c.firm_id == firm_id).order_by(call_log.c.id)
        if engagement_id is not None:
            query = query.where(call_log.c.engagement_id == engagement_id)
        with self.engine.begin() as conn:
            return [dict(row._mapping) for row in conn.execute(query)]
