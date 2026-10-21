from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.auth.security import create_session_token
from app.config import Settings, get_settings
from app.main import create_app


def test_unconfigured_email_sign_in_fails_explicitly() -> None:
    app = create_app()
    app.dependency_overrides[get_settings] = lambda: Settings(
        _env_file=None, session_secret=SecretStr("x" * 32),
    )
    with TestClient(app) as client:
        capabilities = client.get("/auth/capabilities")
        assert capabilities.json() == {"password_sign_in": True, "magic_link": False}
        response = client.post("/auth/magic-link", json={"email": "synthetic@example.invalid"})
        assert response.status_code == 503
        assert response.json() == {"detail": "Email sign-in is not configured"}


def test_short_session_secret_cannot_issue_session() -> None:
    with pytest.raises(RuntimeError, match="at least 32 bytes"):
        create_session_token(
            user_id="synthetic-user", session_id="synthetic-session",
            settings=Settings(_env_file=None, session_secret=SecretStr("short")),
            now=datetime.now(UTC),
        )
