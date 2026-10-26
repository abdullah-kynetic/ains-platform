"""Apply Monday additive revisions to a populated prior schema on real Postgres."""
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import text

from app.database.models import Base
from tests.test_audit_postgres import postgres_engine as postgres_engine


def test_monday_additive_schema_preserves_rows(postgres_engine):
    engine = postgres_engine
    Base.metadata.create_all(engine)
    with engine.begin() as connection:
        connection.execute(text('DROP TABLE engagement_reports'))
        connection.execute(text(
            'ALTER TABLE checklist_item_instances DROP COLUMN na_previous_state'
        ))
        connection.execute(text("INSERT INTO firms (id, name, slug, created_at) VALUES "
                                "('synthetic-before', 'Synthetic before', "
                                "'synthetic-before', now())"))
        config = Config('alembic.ini')
        config.attributes['connection'] = connection
        command.stamp(config, 'a112_auditor_invoices')
        command.upgrade(config, 'head')
        name = connection.scalar(text("SELECT name FROM firms WHERE id='synthetic-before'"))
        assert name == 'Synthetic before'
        assert compare_metadata(MigrationContext.configure(connection), Base.metadata) == []
