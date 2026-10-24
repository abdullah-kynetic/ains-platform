from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.main import app, create_app


def test_health() -> None:
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_openapi_uses_public_brand() -> None:
    client = TestClient(app)
    assert client.get("/openapi.json").json()["info"]["title"] == "Kien Solutions"


def test_local_dev_cors_includes_portal_origin(monkeypatch) -> None:
    assert Settings.model_fields["cors_origins"].default == "http://localhost:3000"
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:3000")
    get_settings.cache_clear()
    try:
        local = Settings(_env_file=None)
        assert local.parsed_cors_origins() == ["http://localhost:3000"]
        client = TestClient(create_app())
        response = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "authorization,content-type",
            },
        )
    finally:
        get_settings.cache_clear()
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert response.headers["access-control-allow-credentials"] == "true"


def test_production_cors_config_excludes_localhost() -> None:
    production = Settings(
        _env_file=None,
        cors_origins="https://kiensolutions.com,https://www.kiensolutions.com",
        portal_url="https://kiensolutions.com",
    )
    origins = production.parsed_cors_origins()
    assert origins == ["https://kiensolutions.com", "https://www.kiensolutions.com"]
    assert all("localhost" not in origin for origin in origins)
