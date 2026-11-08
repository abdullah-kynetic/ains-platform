"""Additive profile migration parity and reversible local PostgreSQL upgrade."""

import os

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, inspect, select
from sqlalchemy.orm import Session

from app.database.models import Base, Firm
from tests.test_audit_postgres import postgres_engine as postgres_engine


def test_profile_upgrade_downgrade_preserves_existing_firms(request):
    url = os.environ.get("KIEN_TEST_POSTGRES_URL")
    engine = create_engine(url) if url else request.getfixturevalue("postgres_engine")
    try:
        new_tables = {"client_contacts", "client_profile_details"}
        Base.metadata.create_all(
            engine,
            tables=[
                table for name, table in Base.metadata.tables.items() if name not in new_tables
            ],
        )
        with Session(engine) as db:
            db.add(
                Firm(id="synthetic-existing", name="Synthetic Existing", slug="synthetic-existing")
            )
            db.commit()
        with engine.begin() as connection:
            # Model now includes the a117 columns; remove them to start from the a115 schema.
            for column in (
                "response_request_text",
                "response_released_at",
                "response_released_by_id",
            ):
                connection.exec_driver_sql(
                    f"ALTER TABLE checklist_item_instances DROP COLUMN {column}"
                )
            original = set(inspect(connection).get_table_names())
            config = Config("alembic.ini")
            config.attributes["connection"] = connection
            command.stamp(config, "a115_user_onboarding")
            command.upgrade(config, "a117_response_requests")
            assert set(inspect(connection).get_table_names()) - original == new_tables | {
                "alembic_version"
            }
            assert compare_metadata(MigrationContext.configure(connection), Base.metadata) == []
            command.downgrade(config, "a115_user_onboarding")
            assert set(inspect(connection).get_table_names()) == original | {"alembic_version"}
            assert connection.scalar(select(Firm.id)) == "synthetic-existing"
            command.upgrade(config, "a117_response_requests")
            assert compare_metadata(MigrationContext.configure(connection), Base.metadata) == []
    finally:
        if url:
            engine.dispose()
