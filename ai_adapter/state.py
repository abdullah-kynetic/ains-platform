"""Durable counters for the adapter: daily request cap and consecutive errors."""

from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import Column, Integer, MetaData, String, Table, create_engine, text
from sqlalchemy.engine import make_url

_meta = MetaData()
counters = Table(
    "ai_counters", _meta, Column("key", String(80), primary_key=True), Column("value", Integer)
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
