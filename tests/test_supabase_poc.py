from __future__ import annotations

import pytest
from pydantic import SecretStr
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.config import Settings
from app.database.models import Base, Firm
from scripts.supabase_poc import (
    ensure_no_existing_application_data,
    validated_supabase_url,
    verify_rolled_back_tenant_isolation,
)


def settings(url: str, *, acknowledged: bool = True) -> Settings:
    return Settings(
        _env_file=None,
        supabase_poc_database_url=SecretStr(url),
        supabase_poc_synthetic_only=acknowledged,
    )


def test_supabase_url_requires_explicit_synthetic_only_acknowledgement() -> None:
    with pytest.raises(ValueError, match="SUPABASE_POC_SYNTHETIC_ONLY"):
        validated_supabase_url(
            settings(
                "postgresql://synthetic:password@db.synthetic.supabase.co:5432/postgres"
                "?sslmode=require",
                acknowledged=False,
            )
        )


@pytest.mark.parametrize(
    "url,error",
    [
        (
            "sqlite:///synthetic.db",
            "PostgreSQL",
        ),
        (
            "postgresql://synthetic:password@localhost:5432/postgres?sslmode=require",
            "Supabase database or pooler host",
        ),
        (
            "postgresql://synthetic:password@db.synthetic.supabase.co:5432/postgres",
            "sslmode=require",
        ),
    ],
)
def test_supabase_url_rejects_unsafe_targets(url: str, error: str) -> None:
    with pytest.raises(ValueError, match=error):
        validated_supabase_url(settings(url))


def test_invalid_supabase_url_does_not_echo_the_credential() -> None:
    credential = "synthetic-secret-that-must-not-be-printed"
    with pytest.raises(ValueError) as exc_info:
        validated_supabase_url(settings(f"not-a-url:{credential}"))

    assert credential not in str(exc_info.value)


def test_supabase_url_accepts_direct_and_pooler_tls_connections() -> None:
    direct = validated_supabase_url(
        settings(
            "postgresql://synthetic:password@db.synthetic.supabase.co:5432/postgres"
            "?sslmode=require"
        )
    )
    pooler = validated_supabase_url(
        settings(
            "postgresql+psycopg://synthetic:password@aws-0-region.pooler.supabase.com:5432/postgres"
            "?sslmode=verify-full"
        )
    )

    assert direct.drivername == "postgresql+psycopg"
    assert pooler.drivername == "postgresql+psycopg"


def test_synthetic_tenant_probe_rolls_back_all_rows() -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    verify_rolled_back_tenant_isolation(engine)

    engine.dispose()


def test_supabase_migration_guard_refuses_existing_application_data() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:", poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(Firm(name="Existing Firm", slug="existing-firm"))
        session.commit()

    with engine.connect() as connection:
        with pytest.raises(RuntimeError, match="already contains AINS application data"):
            ensure_no_existing_application_data(connection)

    engine.dispose()
