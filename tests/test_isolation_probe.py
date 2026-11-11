"""The isolation screen's real second-firm id: gated, auditor-only, never an assigned firm."""

from app.config import get_settings
from app.database.models import Engagement
from tests.test_backend_api import backend, sign_in_auditor, sign_in_client  # noqa: F401


def _enable(monkeypatch):
    monkeypatch.setenv("ISOLATION_PROBE_ENABLED", "true")
    get_settings.cache_clear()


def test_off_by_default_answers_404(backend, monkeypatch):  # noqa: F811
    client, *_ = backend
    monkeypatch.delenv("ISOLATION_PROBE_ENABLED", raising=False)
    get_settings.cache_clear()
    sign_in_auditor(client)
    assert client.get("/auditor/isolation-probe").status_code == 404


def test_returns_a_real_foreign_engagement_and_it_is_really_denied(backend, monkeypatch):  # noqa: F811
    client, factory, ids, *_ = backend
    _enable(monkeypatch)
    try:
        with factory() as db:  # the fixture auditor is assigned to both; firm B is "the other firm"
            db.get(Engagement, ids["engagement_b"]).auditor_id = None
            db.commit()
        sign_in_auditor(client)
        assert client.get("/auditor/isolation-probe").status_code == 200
        probe = client.get("/auditor/isolation-probe")
        assert probe.status_code == 200
        body = probe.json()
        assert body["foreignEngagementId"] == ids["engagement_b"]
        assert body["foreignFirmId"] == ids["firm_b"]
        assert body["foreignEngagementId"] != ids["engagement_a"]
        # Not a random id: it exists, and the server still refuses it.
        for tail in ("/summary", "/findings", "/signoff"):
            denied = client.get(f"/auditor/engagements/{body['foreignEngagementId']}{tail}")
            assert denied.status_code in {403, 404}
        assert client.get(f"/auditor/audit-log?firm_id={body['foreignFirmId']}").status_code in {
            403,
            404,
        }
    finally:
        get_settings.cache_clear()


def test_clients_and_anonymous_cannot_use_it(backend, monkeypatch):  # noqa: F811
    client, *_ = backend
    _enable(monkeypatch)
    try:
        assert client.get("/auditor/isolation-probe").status_code == 401
        sign_in_client(client)
        assert client.get("/auditor/isolation-probe").status_code == 403
    finally:
        get_settings.cache_clear()
