"""a120 adds workflow columns and tables additively and backfills existing rows."""

from datetime import UTC, date, datetime

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

from app.database.models import Base


def test_workflow_migration_downgrades_and_upgrades_with_backfill():
    config = Config("alembic.ini")
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with engine.begin() as connection:
        config.attributes["connection"] = connection
        command.stamp(config, "a120_workflow_routes")
        command.downgrade(config, "a119_firm_logo_url")
        inspector = inspect(connection)
        assert "document_issues" not in inspector.get_table_names()
        assert "number" not in {c["name"] for c in inspector.get_columns("documents")}
        now = datetime.now(UTC).isoformat(sep=" ")
        connection.execute(
            text(
                "INSERT INTO firms (id, name, slug, created_at) VALUES ('f', 'Synthetic', 's', :n)"
            ),
            {"n": now},
        )
        connection.execute(
            text(
                "INSERT INTO engagements (id, firm_id, engagement_type, status, "
                "review_period_start, review_period_end, created_at, updated_at) "
                "VALUES ('e1', 'f', 't', 'COLLECTING',"
                " :a, :b, :n, :n), ('e2', 'f', 't', 'DRAFT', :a, :b, :n, :n)"
            ),
            {"a": date(2025, 1, 1), "b": date(2025, 12, 31), "n": now},
        )
        connection.execute(
            text(
                "INSERT INTO users (id, email, name, role, is_active, mfa_enabled, invited_at, "
                "created_at) VALUES ('u', 'u@example.test', 'U', 'client', 1, 0, :n, :n)"
            ),
            {"n": now},
        )
        for index in range(3):
            connection.execute(
                text(
                    "INSERT INTO documents (id, firm_id, engagement_id, uploaded_by_id, "
                    "original_name, size_bytes, egnyte_path, sha256, version, created_at) VALUES "
                    "(:i, 'f', 'e1', 'u', 'x', 1, :p, 'a', '1', :n)"
                ),
                {"i": f"d{index}", "p": f"/p{index}", "n": now},
            )
        command.upgrade(config, "a120_workflow_routes")
        numbers = (
            connection.execute(text("SELECT number FROM documents ORDER BY number")).scalars().all()
        )
        assert numbers == ["1.1", "1.2", "1.3"]
        rows = dict(connection.execute(text("SELECT id, document_seq FROM engagements")).all())
        assert rows == {"e1": 3, "e2": 0}
        sent = dict(
            connection.execute(
                text("SELECT id, checklist_sent_at IS NOT NULL FROM engagements")
            ).all()
        )
        assert sent == {"e1": 1, "e2": 0}  # only non-draft engagements count as dispatched
        assert {"document_issues", "issue_messages", "document_item_links"} <= set(
            inspect(connection).get_table_names()
        )
    engine.dispose()
