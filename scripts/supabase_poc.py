"""Migrate and verify an isolated, synthetic-only Supabase PostgreSQL project.

This command intentionally does not use Supabase Auth, Storage, or service-role keys. It
accepts only Supabase PostgreSQL hosts using TLS, never prints the connection URL, and rolls
back its synthetic tenant-isolation probe.
"""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path
from uuid import uuid4

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import URL, Engine, create_engine, func, inspect, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError
from sqlalchemy.orm import Session
from sqlalchemy.pool import NullPool

from app.api.engagements import visible_engagements
from app.config import Settings, get_settings
from app.database.models import Base, Engagement, Firm, User, UserRole

ROOT = Path(__file__).resolve().parents[1]
ALLOWED_SSL_MODES = {"require", "verify-ca", "verify-full"}


def validated_supabase_url(settings: Settings) -> URL:
    """Return a psycopg URL only after the synthetic-only and TLS guards pass."""

    if not settings.supabase_poc_synthetic_only:
        raise ValueError(
            "Set SUPABASE_POC_SYNTHETIC_ONLY=true only for an isolated synthetic project"
        )
    raw_url = settings.supabase_poc_database_url.get_secret_value().strip()
    if not raw_url:
        raise ValueError("SUPABASE_POC_DATABASE_URL is required")

    try:
        url = make_url(raw_url)
    except ArgumentError:
        raise ValueError("SUPABASE_POC_DATABASE_URL is not a valid SQLAlchemy URL") from None
    if url.drivername not in {"postgresql", "postgresql+psycopg"}:
        raise ValueError("The Supabase PoC requires a PostgreSQL connection URL")
    host = (url.host or "").casefold().rstrip(".")
    if not (host.endswith(".supabase.co") or host.endswith(".pooler.supabase.com")):
        raise ValueError("The PoC connection must use a Supabase database or pooler host")
    if url.query.get("sslmode") not in ALLOWED_SSL_MODES:
        raise ValueError("The Supabase PoC connection must include sslmode=require or stronger")
    if url.drivername == "postgresql":
        url = url.set(drivername="postgresql+psycopg")
    return url


def poc_engine(settings: Settings) -> Engine:
    return create_engine(
        validated_supabase_url(settings),
        poolclass=NullPool,
        pool_pre_ping=True,
        connect_args={"connect_timeout": 10},
    )


def alembic_config() -> Config:
    return Config(str(ROOT / "alembic.ini"))


def ensure_no_existing_application_data(connection) -> None:
    """Refuse to migrate a database that already contains AINS application records."""

    schema = "public" if connection.dialect.name == "postgresql" else None
    existing_tables = set(inspect(connection).get_table_names(schema=schema))
    for table in Base.metadata.sorted_tables:
        if table.name not in existing_tables:
            continue
        row_count = connection.scalar(select(func.count()).select_from(table))
        if row_count:
            raise RuntimeError(
                "Supabase PoC migration refused: the target already contains AINS application data"
            )


def migrate(engine: Engine) -> None:
    config = alembic_config()
    with engine.connect() as connection:
        ensure_no_existing_application_data(connection)
    with engine.connect() as connection:
        config.attributes["connection"] = connection
        command.upgrade(config, "head")


def verify_migration_head(connection) -> None:
    config = alembic_config()
    expected_head = ScriptDirectory.from_config(config).get_current_head()
    actual_head = connection.scalar(text("SELECT version_num FROM alembic_version"))
    if actual_head != expected_head:
        raise RuntimeError(
            "Supabase schema is not at the repository migration head; run the migrate command"
        )


def verify_rolled_back_tenant_isolation(engine: Engine) -> None:
    """Exercise real ORM tenant scopes without leaving synthetic rows behind."""

    marker = uuid4().hex
    firm_a = Firm(name="Synthetic Supabase Alpha", slug=f"supabase-poc-alpha-{marker}")
    firm_b = Firm(name="Synthetic Supabase Beta", slug=f"supabase-poc-beta-{marker}")
    client_a = User(
        firm=firm_a,
        email=f"supabase-poc-client-a-{marker}@example.test",
        name="Synthetic Supabase Client A",
        role=UserRole.CLIENT,
    )
    client_b = User(
        firm=firm_b,
        email=f"supabase-poc-client-b-{marker}@example.test",
        name="Synthetic Supabase Client B",
        role=UserRole.CLIENT,
    )
    auditor_a = User(
        email=f"supabase-poc-auditor-a-{marker}@example.test",
        name="Synthetic Supabase Auditor A",
        role=UserRole.AUDITOR,
    )
    auditor_b = User(
        email=f"supabase-poc-auditor-b-{marker}@example.test",
        name="Synthetic Supabase Auditor B",
        role=UserRole.AUDITOR,
    )
    engagement_a = Engagement(
        firm=firm_a,
        auditor=auditor_a,
        review_period_start=date(2026, 1, 1),
        review_period_end=date(2026, 12, 31),
    )
    engagement_b = Engagement(
        firm=firm_b,
        auditor=auditor_b,
        review_period_start=date(2026, 1, 1),
        review_period_end=date(2026, 12, 31),
    )

    with engine.connect() as connection:
        transaction = connection.begin()
        session = Session(bind=connection, expire_on_commit=False)
        try:
            session.add_all(
                [
                    firm_a,
                    firm_b,
                    client_a,
                    client_b,
                    auditor_a,
                    auditor_b,
                    engagement_a,
                    engagement_b,
                ]
            )
            session.flush()

            client_visible = session.scalars(visible_engagements(client_a)).all()
            auditor_visible = session.scalars(visible_engagements(auditor_a)).all()
            if [engagement.id for engagement in client_visible] != [engagement_a.id]:
                raise RuntimeError("Client tenant isolation verification failed")
            if [engagement.id for engagement in auditor_visible] != [engagement_a.id]:
                raise RuntimeError("Auditor assignment isolation verification failed")
        finally:
            transaction.rollback()
            session.close()

    with engine.connect() as connection:
        remaining = connection.scalar(select(Firm.id).where(Firm.slug == firm_a.slug))
        if remaining is not None:
            raise RuntimeError("Synthetic Supabase verification rows were not rolled back")


def verify(engine: Engine) -> None:
    with engine.connect() as connection:
        verify_migration_head(connection)
    verify_rolled_back_tenant_isolation(engine)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action",
        choices=("migrate", "verify", "run"),
        help="apply migrations, verify the current schema, or perform both",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    engine = poc_engine(get_settings())
    try:
        if args.action in {"migrate", "run"}:
            migrate(engine)
        if args.action in {"verify", "run"}:
            verify(engine)
    finally:
        engine.dispose()
    print("Synthetic Supabase PostgreSQL PoC completed successfully.")


if __name__ == "__main__":
    main()
