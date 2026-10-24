from fastapi.testclient import TestClient

from app.main import app


def test_health() -> None:
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_openapi_uses_public_brand() -> None:
    client = TestClient(app)
    assert client.get("/openapi.json").json()["info"]["title"] == "Kien Solutions"
