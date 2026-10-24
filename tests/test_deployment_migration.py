"""Verify the entrypoint's single migration head and the recovery schema migration."""

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect

from app.database.models import Base


def test_password_recovery_migration_up_and_down():
    config = Config("alembic.ini")
    assert ScriptDirectory.from_config(config).get_heads() == ["a109_password_reset"]
    engine = create_engine("sqlite://")
    tables = [
        table
        for name, table in Base.metadata.tables.items()
        if name not in {"password_reset_tokens", "auth_rate_limits"}
    ]
    Base.metadata.create_all(engine, tables=tables)
    with engine.begin() as connection:
        config.attributes["connection"] = connection
        command.stamp(config, "8ad73a592bc1")
        command.upgrade(config, "head")
        names = inspect(connection).get_table_names()
        assert "password_reset_tokens" in names
        assert "auth_rate_limits" in names
        indexes = inspect(connection).get_indexes("password_reset_tokens")
        assert any(index["unique"] and index["column_names"] == ["token_hash"] for index in indexes)
        command.downgrade(config, "8ad73a592bc1")
        assert "password_reset_tokens" not in inspect(connection).get_table_names()
    engine.dispose()
