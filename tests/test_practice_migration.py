"""a121 adds the practice tables additively and puts existing auditors in one practice."""

from datetime import UTC, datetime

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

from app.database.models import Base


def _user(connection, user_id: str, role: str, created: str) -> None:
    connection.execute(
        text(
            "INSERT INTO users (id, email, name, role, is_active, mfa_enabled, invited_at, "
            "created_at) VALUES (:i, :e, :i, :r, 1, 0, :c, :c)"
        ),
        {"i": user_id, "e": f"{user_id}@example.test", "r": role, "c": created},
    )


def test_practice_migration_downgrades_and_upgrades_with_backfill():
    config = Config("alembic.ini")
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with engine.begin() as connection:
        config.attributes["connection"] = connection
        command.stamp(config, "a121_practice_routes")
        command.downgrade(config, "a120_workflow_routes")
        inspector = inspect(connection)
        assert "practices" not in inspector.get_table_names()
        assert "practice_id" not in {c["name"] for c in inspector.get_columns("users")}
        now = datetime.now(UTC).isoformat(sep=" ")
        _user(connection, "second", "AUDITOR", now)
        _user(connection, "first", "AUDITOR", "2020-01-01 00:00:00")
        _user(connection, "client", "CLIENT", now)
        command.upgrade(config, "a121_practice_routes")
        rows = {
            row[0]: row[1:]
            for row in connection.execute(
                text("SELECT id, practice_id IS NOT NULL, team_role FROM users")
            )
        }
        assert rows == {
            "first": (1, "partner"),  # earliest auditor can invite the rest
            "second": (1, "auditor"),
            "client": (0, None),  # clients are untouched
        }
        assert connection.execute(text("SELECT count(*) FROM practices")).scalar() == 1
        assert {"practice_rubric_items", "practice_templates"} <= set(
            inspect(connection).get_table_names()
        )
    engine.dispose()


def test_practice_migration_is_idempotent_on_current_schema():
    """Postgres CI builds the schema from the models, then runs every migration over it."""
    config = Config("alembic.ini")
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with engine.begin() as connection:
        config.attributes["connection"] = connection
        command.stamp(config, "a120_workflow_routes")
        command.upgrade(config, "a121_practice_routes")
        assert "practices" in inspect(connection).get_table_names()
    engine.dispose()
