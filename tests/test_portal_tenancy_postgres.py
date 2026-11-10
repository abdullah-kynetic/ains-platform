"""Portal migrations preserve existing synthetic firms and reverse additive schema."""

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError

from app.database.models import Base
from tests.test_audit_postgres import postgres_engine as postgres_engine


def test_portal_upgrade_downgrade_preserves_existing_firms(postgres_engine):
    Base.metadata.create_all(postgres_engine)
    config = Config("alembic.ini")
    with postgres_engine.begin() as connection:
        connection.exec_driver_sql("ALTER TABLE firms DROP COLUMN logo_url")
        connection.execute(
            text(
                "INSERT INTO firms (id, name, slug, created_at) "
                "VALUES ('synthetic-legacy', 'Synthetic Legacy', 'Synthetic-Legacy', now())"
            )
        )
        config.attributes["connection"] = connection
        command.stamp(config, "a117_response_requests")
        command.upgrade(config, "a119_firm_logo_url")
        assert connection.scalar(text("SELECT slug FROM firms")) == "synthetic-legacy"
        assert connection.scalar(text("SELECT logo_url FROM firms")) is None
        assert "ck_firms_portal_slug" in {
            check["name"] for check in inspect(connection).get_check_constraints("firms")
        }
        for invalid in ("auditor", "UPPERCASE", "bad.label", "-bad"):
            with pytest.raises(IntegrityError), connection.begin_nested():
                connection.execute(text("UPDATE firms SET slug = :slug"), {"slug": invalid})
        command.downgrade(config, "a117_response_requests")
        assert "logo_url" not in {c["name"] for c in inspect(connection).get_columns("firms")}
        assert "ck_firms_portal_slug" not in {
            check["name"] for check in inspect(connection).get_check_constraints("firms")
        }
        assert connection.scalar(text("SELECT name FROM firms")) == "Synthetic Legacy"
        command.upgrade(config, "a119_firm_logo_url")
        assert connection.scalar(text("SELECT slug FROM firms")) == "synthetic-legacy"
