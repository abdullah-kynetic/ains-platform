"""S-11: private configuration is redacted and browser environment names are explicitly public."""

import ast
import re
from pathlib import Path

from pydantic import SecretStr
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.auth.security import verify_password
from app.config import Settings
from app.database.models import Base, User

PUBLIC_NAMES = {
    "NEXT_PUBLIC_API_URL",
    "NEXT_PUBLIC_AUDITOR_HOST",
    "NEXT_PUBLIC_MAX_UPLOAD_MB",
    "NEXT_PUBLIC_SENTRY_DSN",
    "NEXT_PUBLIC_USE_MOCKS",
}


def test_browser_public_configuration_has_no_private_names():
    found = set()
    for path in Path("web/src").rglob("*"):
        if path.suffix in {".ts", ".tsx"}:
            found.update(re.findall(r"NEXT_PUBLIC_[A-Z0-9_]+", path.read_text()))
    assert found == PUBLIC_NAMES


def test_private_settings_use_secretstr_and_redact_database_credentials():
    for name in (
        "session_secret",
        "resend_api_key",
        "database_url",
        "demo_password",
        "egnyte_password",
        "egnyte_access_token",
        "egnyte_refresh_token",
    ):
        assert Settings.model_fields[name].annotation is SecretStr
    settings = Settings(
        _env_file=None,
        database_url="postgresql+psycopg://synthetic:synthetic-password@localhost/synthetic",
    )
    assert "synthetic-password" not in repr(settings)
    assert "synthetic-password" not in settings.model_dump_json()


def test_workflow_environment_reads_are_centralized():
    for path in Path("app").rglob("*.py"):
        if path == Path("app/config.py"):
            continue
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module == "os":
                if any(name.name in {"environ", "getenv"} for name in node.names):
                    raise AssertionError(f"Environment reads belong in app/config.py: {path}")
            if isinstance(node, ast.Attribute) and node.attr in {"environ", "getenv"}:
                raise AssertionError(
                    f"Environment configuration must go through app/config.py: {path}"
                )


def test_demo_password_is_loaded_through_private_settings(monkeypatch):
    import app.demo_seed as demo

    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine)
    settings = Settings(_env_file=None, demo_password="synthetic-demo-password")
    monkeypatch.setattr(demo, "get_settings", lambda: settings)
    monkeypatch.setattr(demo, "get_session_factory", lambda: factory)
    try:
        demo.seed()
        with factory() as db:
            users = db.scalars(select(User)).all()
            assert len(users) == 2
            assert all(
                verify_password("synthetic-demo-password", user.password_hash) for user in users
            )
    finally:
        engine.dispose()
