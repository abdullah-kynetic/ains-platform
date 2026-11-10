"""Portal slug, host binding, CORS and email links. Synthetic firms only."""

from __future__ import annotations

import json
from collections.abc import Iterator
from datetime import UTC, date, datetime, timedelta
from urllib.parse import parse_qs, urlparse

import httpx
import pyotp
import pytest
import respx
from fastapi import Request
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.email import ResendSender
from app.auth.security import hash_password, new_invitation_token
from app.config import Settings, get_settings
from app.cors import allowed_cors_origin
from app.database.models import (
    AuthSession,
    Base,
    ClientInvitation,
    Engagement,
    Firm,
    User,
    UserRole,
)
from app.database.session import get_db
from app.main import create_app
from app.tenancy import (
    RESERVED_SLUGS,
    SlugCache,
    allocate_firm_slug,
    portal_url_for,
    require_firm_slug,
    require_logo_url,
    resolve_portal,
)

CLIENT_PASSWORD = "synthetic-client-password"
AUDITOR_PASSWORD = "synthetic-auditor-password"
MFA_SECRET = "JBSWY3DPEHPK3PXP"
BASE = "kiensolutions.com"


def _request(headers: dict[str, str]) -> Request:
    raw = [(key.lower().encode(), value.encode()) for key, value in headers.items()]
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": raw,
        "query_string": b"",
        "scheme": "https",
        "server": (BASE, 443),
        "client": ("127.0.0.1", 1234),
    }
    return Request(scope)


def _settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "session_secret": SecretStr("synthetic-test-session-secret-at-least-32-bytes"),
        "session_cookie_secure": False,
        "portal_base_domain": BASE,
        "portal_url": "https://{slug}.kiensolutions.com",
        "cors_origins": "http://localhost:3000",
        "resend_api_key": SecretStr("synthetic-key"),
        "email_from": "synthetic@example.test",
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)  # type: ignore[arg-type]


def test_slug_rejects_reserved_and_non_labels() -> None:
    require_firm_slug("kynetic")
    for reserved in RESERVED_SLUGS:
        with pytest.raises(ValueError):
            require_firm_slug(reserved)
    for bad in ("Kynetic", "kynetic.com", "-kynetic", "kynetic-", "a" * 64, "has space", ""):
        with pytest.raises(ValueError):
            Firm(name="Synthetic", slug=bad)


def test_allocate_skips_reserved_and_collisions() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine)
    with factory() as db:
        db.add(Firm(name="Synthetic Client", slug="client"))
        db.commit()
        assert allocate_firm_slug(db, "API") == "api-2"
        assert allocate_firm_slug(db, "Client") == "client-2"
        assert allocate_firm_slug(db, "Mail") == "mail-2"
    engine.dispose()


def test_portal_url_template_and_auditor_host() -> None:
    settings = _settings()
    assert portal_url_for(settings, "kynetic") == "https://kynetic.kiensolutions.com"
    assert portal_url_for(settings, None) == "https://auditor.kiensolutions.com"
    decision = resolve_portal(_request({"origin": portal_url_for(settings, None)}), settings)
    assert decision.kind == "auditor"
    local = _settings(portal_url="http://localhost:3000")
    assert portal_url_for(local, None) == "http://localhost:3000"
    with pytest.raises(ValueError):
        portal_url_for(settings, "evil.example/path")


@pytest.mark.parametrize(
    "value",
    [
        "//external.example/logo.svg",
        "https://",
        "https://user:pass@example.test/logo",
        "https://example.test:bad/logo",
    ],
)
def test_logo_rejects_network_paths_and_malformed_https(value) -> None:
    with pytest.raises(ValueError):
        require_logo_url(value)


def test_slug_cache_reuses_a_load_until_cleared() -> None:
    cache = SlugCache(ttl_seconds=60)
    calls = {"n": 0}

    def load() -> set[str]:
        calls["n"] += 1
        return {"kynetic"}

    assert cache.get(load) == frozenset({"kynetic"})
    assert cache.get(load) == frozenset({"kynetic"})
    assert calls["n"] == 1
    cache.clear()
    assert cache.get(load) == frozenset({"kynetic"})
    assert calls["n"] == 2


def test_resolve_portal_prefers_agreeing_firm_origin() -> None:
    settings = _settings()
    firm = resolve_portal(
        _request(
            {
                "host": f"api.{BASE}",
                "origin": "https://kynetic.kiensolutions.com",
            }
        ),
        settings,
    )
    assert firm.kind == "firm" and firm.slug == "kynetic"
    conflict = resolve_portal(
        _request(
            {
                "origin": "https://kynetic.kiensolutions.com",
                "x-forwarded-host": "otherfirm.kiensolutions.com",
            }
        ),
        settings,
    )
    assert conflict.kind == "conflict"
    assert resolve_portal(_request({"origin": "https://www.kiensolutions.com"}), settings).kind == (
        "landing"
    )
    assert resolve_portal(_request({"host": f"admin.{BASE}"}), settings).kind == "reserved"
    assert resolve_portal(_request({"host": "testserver"}), settings).kind == "absent"
    disabled = resolve_portal(_request({"host": "testserver"}), _settings(portal_base_domain=""))
    assert disabled.enforced is False


def test_dev_localhost_origin_is_off_in_production() -> None:
    slugs = frozenset({"synthetic-alpha"})
    dev = _settings(portal_base_domain="", session_cookie_secure=False, cors_origins="")
    origin = "http://synthetic-alpha.localhost:3000"
    assert allowed_cors_origin(origin, dev, slugs) == origin
    assert allowed_cors_origin("http://synthetic-alpha.localhost:3100", dev, slugs) == (
        "http://synthetic-alpha.localhost:3100"
    )
    assert allowed_cors_origin("http://missing.localhost:3000", dev, slugs) is None
    assert allowed_cors_origin("http://api.localhost:3000", dev, slugs) is None
    assert allowed_cors_origin("https://synthetic-alpha.localhost:3000", dev, slugs) is None

    prod = _settings(cors_origins=origin)
    assert allowed_cors_origin(origin, prod, slugs) is None
    secure_only = _settings(portal_base_domain="", session_cookie_secure=True, cors_origins=origin)
    assert allowed_cors_origin(origin, secure_only, slugs) is None

    dev_decision = resolve_portal(
        _request({"origin": origin, "host": "localhost:8000"}),
        dev,
    )
    assert dev_decision.kind == "firm" and dev_decision.slug == "synthetic-alpha"
    prod_decision = resolve_portal(
        _request({"origin": origin, "host": f"api.{BASE}"}),
        prod,
    )
    assert prod_decision.kind != "firm"


def test_cors_allows_apex_www_and_known_slugs_only() -> None:
    settings = _settings(cors_origins="http://localhost:3000")
    slugs = frozenset({"synthetic-alpha"})
    assert (
        allowed_cors_origin("https://synthetic-alpha.kiensolutions.com", settings, slugs)
        == "https://synthetic-alpha.kiensolutions.com"
    )
    assert allowed_cors_origin("https://kiensolutions.com", settings, slugs) == (
        "https://kiensolutions.com"
    )
    assert allowed_cors_origin("https://www.kiensolutions.com", settings, slugs) == (
        "https://www.kiensolutions.com"
    )
    assert allowed_cors_origin("http://localhost:3000", settings, slugs) == "http://localhost:3000"
    for denied in (
        "https://synthetic-beta.kiensolutions.com",
        "https://api.kiensolutions.com",
        "https://admin.kiensolutions.com",
        "https://synthetic-alpha.kiensolutions.com.evil.test",
        "https://evil.example",
        "http://synthetic-alpha.kiensolutions.com",
        "*",
    ):
        assert allowed_cors_origin(denied, settings, slugs) is None


@pytest.fixture
def portal() -> Iterator[tuple[TestClient, sessionmaker[Session], dict[str, str]]]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    ids: dict[str, str] = {}
    with factory() as db:
        firm_a = Firm(name="Synthetic Alpha Securities", slug="synthetic-alpha")
        firm_b = Firm(name="Synthetic Beta Securities", slug="synthetic-beta")
        db.add_all([firm_a, firm_b])
        db.flush()
        client_a = User(
            firm_id=firm_a.id,
            email="alpha-client@example.test",
            name="Synthetic Alpha Client",
            role=UserRole.CLIENT,
            password_hash=hash_password(CLIENT_PASSWORD),
            accepted_at=datetime.now(UTC),
        )
        client_b = User(
            firm_id=firm_b.id,
            email="beta-client@example.test",
            name="Synthetic Beta Client",
            role=UserRole.CLIENT,
            password_hash=hash_password(CLIENT_PASSWORD),
            accepted_at=datetime.now(UTC),
        )
        inactive = User(
            firm_id=firm_a.id,
            email="inactive-alpha@example.test",
            name="Synthetic Inactive",
            role=UserRole.CLIENT,
            is_active=False,
            password_hash=hash_password(CLIENT_PASSWORD),
        )
        auditor = User(
            email="auditor@example.test",
            name="Synthetic Auditor",
            role=UserRole.AUDITOR,
            password_hash=hash_password(AUDITOR_PASSWORD),
            mfa_secret=MFA_SECRET,
            mfa_enabled=True,
            accepted_at=datetime.now(UTC),
        )
        db.add_all([client_a, client_b, inactive, auditor])
        db.flush()
        engagement = Engagement(
            firm_id=firm_a.id,
            auditor_id=auditor.id,
            review_period_start=date(2025, 1, 1),
            review_period_end=date(2025, 12, 31),
        )
        db.add(engagement)
        db.flush()
        token, token_hash = new_invitation_token()
        db.add(
            ClientInvitation(
                firm_id=firm_b.id,
                engagement_id=engagement.id,
                email="invitee@example.test",
                name="Synthetic Invitee",
                token_hash=token_hash,
                expires_at=datetime.now(UTC) + timedelta(hours=1),
                created_by_id=auditor.id,
            )
        )
        db.commit()
        ids.update(
            firm_a=firm_a.id,
            firm_b=firm_b.id,
            engagement=engagement.id,
            invitation_token=token,
        )
    settings = _settings()
    app = create_app()
    app.state.portal_slugs = frozenset({"synthetic-alpha", "synthetic-beta"})

    def db_override() -> Iterator[Session]:
        with factory() as db:
            yield db

    app.dependency_overrides[get_db] = db_override
    app.dependency_overrides[get_settings] = lambda: settings
    with TestClient(app) as client:
        yield client, factory, ids
    engine.dispose()


def _origin(slug: str) -> dict[str, str]:
    return {"origin": f"https://{slug}.kiensolutions.com"}


def test_cross_tenant_session_is_rejected_and_cookie_is_host_only(portal) -> None:
    client, _, _ids = portal
    wrong = client.post(
        "/auth/password",
        headers=_origin("synthetic-beta"),
        json={"email": "alpha-client@example.test", "password": CLIENT_PASSWORD},
    )
    assert wrong.status_code == 403
    assert "set-cookie" not in wrong.headers

    signed_in = client.post(
        "/auth/password",
        headers=_origin("synthetic-alpha"),
        json={"email": "alpha-client@example.test", "password": CLIENT_PASSWORD},
    )
    assert signed_in.status_code == 200
    cookie = signed_in.headers["set-cookie"]
    assert "domain=" not in cookie.lower()
    assert "samesite=lax" in cookie.lower()
    assert "httponly" in cookie.lower()

    assert client.get("/auth/session", headers=_origin("synthetic-alpha")).status_code == 200
    denied = client.get("/auth/session", headers=_origin("synthetic-beta"))
    assert denied.status_code == 403
    assert denied.json()["detail"] == "Session firm does not match this portal"
    assert (
        denied.headers["access-control-allow-origin"] == "https://synthetic-beta.kiensolutions.com"
    )
    assert denied.headers["access-control-allow-credentials"] == "true"
    assert client.get("/engagements/current", headers=_origin("synthetic-beta")).status_code == 403
    assert client.get("/engagements/current", headers=_origin("synthetic-alpha")).status_code == 200

    client.cookies.clear()
    auditor = client.post(
        "/auth/password",
        headers={**_origin("synthetic-alpha"), "host": f"api.{BASE}"},
        json={
            "email": "auditor@example.test",
            "password": AUDITOR_PASSWORD,
            "mfa_code": pyotp.TOTP(MFA_SECRET).now(),
        },
    )
    assert auditor.status_code == 200
    assert "domain=" not in auditor.headers["set-cookie"].lower()


def test_reserved_and_unknown_hosts_and_conflicting_labels(portal) -> None:
    client, _, ids = portal
    body = {"email": "alpha-client@example.test", "password": CLIENT_PASSWORD}
    reserved = client.post(
        "/auth/password",
        headers={"origin": "https://www.kiensolutions.com"},
        json=body,
    )
    assert reserved.status_code == 403
    assert reserved.json()["detail"] == "Firm portal host is required"
    unknown = client.post("/auth/password", headers=_origin("not-a-firm"), json=body)
    # The cross-site origin check refuses an unknown firm host before sign-in is reached.
    assert unknown.status_code == 403
    assert unknown.json()["detail"] == "Cross-site request refused"
    conflict = client.post(
        "/auth/password",
        headers={
            "origin": "https://synthetic-alpha.kiensolutions.com",
            "x-forwarded-host": "synthetic-beta.kiensolutions.com",
        },
        json=body,
    )
    assert conflict.status_code == 403
    accept = client.post(
        "/auth/invitations/accept",
        headers=_origin("synthetic-alpha"),
        json={"token": ids["invitation_token"], "password": "synthetic-invite-password"},
    )
    assert accept.status_code == 403
    assert "set-cookie" not in accept.headers


def test_secure_cookie_still_omits_domain(portal) -> None:
    client, _, _ids = portal
    client.app.dependency_overrides[get_settings] = lambda: _settings(session_cookie_secure=True)
    response = client.post(
        "/auth/password",
        headers=_origin("synthetic-alpha"),
        json={"email": "alpha-client@example.test", "password": CLIENT_PASSWORD},
    )
    assert response.status_code == 200
    cookie = response.headers["set-cookie"].lower()
    assert "secure" in cookie
    assert "domain=" not in cookie


def test_cors_preflight_allow_and_deny(portal) -> None:
    client, _, _ids = portal
    allowed = client.options(
        "/health",
        headers={
            "origin": "https://synthetic-alpha.kiensolutions.com",
            "access-control-request-method": "POST",
        },
    )
    assert allowed.status_code == 200
    assert allowed.headers["access-control-allow-origin"] == (
        "https://synthetic-alpha.kiensolutions.com"
    )
    assert allowed.headers["access-control-allow-credentials"] == "true"
    assert allowed.headers["access-control-allow-origin"] != "*"
    assert "POST" in allowed.headers["access-control-allow-methods"]

    denied = client.options(
        "/health",
        headers={
            "origin": "https://not-a-firm.kiensolutions.com",
            "access-control-request-method": "POST",
        },
    )
    assert denied.status_code == 400
    assert "access-control-allow-origin" not in denied.headers
    echoed = denied.headers.get("access-control-allow-origin", "")
    assert "not-a-firm.kiensolutions.com" not in echoed

    stray = client.get("/health", headers={"origin": "https://evil.example"})
    assert stray.status_code == 200
    assert "access-control-allow-origin" not in stray.headers


@respx.mock
def test_email_links_use_the_firm_slug(portal) -> None:
    client, factory, ids = portal
    send = respx.post("https://api.resend.com/emails").mock(
        return_value=httpx.Response(200, json={"id": "synthetic"})
    )
    settings = _settings()
    for purpose, path in (
        ("magic-link", "sign-in"),
        ("invitation", "accept-invitation"),
        ("reset", "reset-password"),
    ):
        ResendSender(settings, purpose).send(
            email="alpha-client@example.test",
            token="synthetic-token",
            expires_at=datetime.now(UTC) + timedelta(minutes=5),
            slug="synthetic-alpha",
        )
        body = json.loads(send.calls[-1].request.content)
        link = f"https://synthetic-alpha.kiensolutions.com/{path}?token=synthetic-token"
        assert link in body["text"]
    requested = client.post("/auth/magic-link", json={"email": "alpha-client@example.test"})
    assert requested.status_code == 202
    message = json.loads(send.calls[-1].request.content)["text"]
    link = message.split()[1]
    assert link.startswith("https://synthetic-alpha.kiensolutions.com/sign-in?")
    token = parse_qs(urlparse(link).query)["token"][0]
    denied = client.post(
        "/auth/magic-link/verify",
        headers=_origin("synthetic-beta"),
        json={"token": token},
    )
    assert denied.status_code == 403
    verified = client.post(
        "/auth/magic-link/verify",
        headers=_origin("synthetic-alpha"),
        json={"token": token},
    )
    assert verified.status_code == 200

    client.cookies.clear()
    reset = client.post("/auth/password-reset/request", json={"email": "beta-client@example.test"})
    assert reset.status_code == 202
    reset_text = json.loads(send.calls[-1].request.content)["text"]
    assert "https://synthetic-beta.kiensolutions.com/reset-password?token=" in reset_text


def test_public_branding_returns_only_name_and_logo(portal) -> None:
    client, factory, ids = portal
    with factory() as db:
        firm = db.get(Firm, ids["firm_a"])
        assert firm is not None
        firm.logo_url = "/brand/synthetic-alpha.svg"
        db.commit()
        other_name = db.get(Firm, ids["firm_b"]).name

    branded = client.get("/tenant/branding", headers=_origin("synthetic-alpha"))
    assert branded.status_code == 200
    assert branded.json() == {
        "name": "Synthetic Alpha Securities",
        "logoUrl": "/brand/synthetic-alpha.svg",
    }
    assert set(branded.json()) == {"name", "logoUrl"}
    assert ids["firm_a"] not in branded.text
    assert other_name not in branded.text
    assert "example.test" not in branded.text

    unknown = client.get("/tenant/branding", headers=_origin("not-a-firm"))
    reserved = client.get("/tenant/branding", headers={"origin": "https://www.kiensolutions.com"})
    api_host = client.get("/tenant/branding", headers={"origin": "https://api.kiensolutions.com"})
    assert unknown.status_code == reserved.status_code == api_host.status_code == 404
    for response in (unknown, reserved, api_host):
        assert response.json()["detail"] == "Unknown firm portal"
        assert ids["firm_a"] not in response.text

    dev_origin = {"origin": "http://synthetic-alpha.localhost:3000", "host": "localhost:8000"}
    assert client.get("/tenant/branding", headers=dev_origin).status_code == 404

    client.app.dependency_overrides[get_settings] = lambda: _settings(
        portal_base_domain="", session_cookie_secure=False
    )
    dev_brand = client.get("/tenant/branding", headers=dev_origin)
    assert dev_brand.status_code == 200
    assert dev_brand.json()["name"] == "Synthetic Alpha Securities"
    assert dev_brand.json()["logoUrl"] == "/brand/synthetic-alpha.svg"
    missing = client.get(
        "/tenant/branding",
        headers={"origin": "http://not-a-firm.localhost:3000"},
    )
    assert missing.status_code == 404
    assert (
        client.get(
            "/tenant/branding",
            headers={"origin": "http://api.localhost:3000"},
        ).status_code
        == 404
    )

    preflight = client.options(
        "/tenant/branding",
        headers={
            "origin": "http://synthetic-alpha.localhost:3000",
            "access-control-request-method": "GET",
        },
    )
    assert preflight.status_code == 200
    assert preflight.headers["access-control-allow-origin"] == (
        "http://synthetic-alpha.localhost:3000"
    )
    assert preflight.headers["access-control-allow-credentials"] == "true"

    client.app.dependency_overrides[get_settings] = lambda: _settings(
        cors_origins="http://synthetic-alpha.localhost:3000"
    )
    blocked = client.options(
        "/tenant/branding",
        headers={
            "origin": "http://synthetic-alpha.localhost:3000",
            "access-control-request-method": "GET",
        },
    )
    assert blocked.status_code == 400
    assert "access-control-allow-origin" not in blocked.headers


def test_dev_localhost_session_binds_the_firm(portal) -> None:
    client, _, _ids = portal
    client.app.dependency_overrides[get_settings] = lambda: _settings(
        portal_base_domain="", session_cookie_secure=False
    )
    alpha = {"origin": "http://synthetic-alpha.localhost:3000", "host": "localhost:8000"}
    beta = {"origin": "http://synthetic-beta.localhost:3000", "host": "localhost:8000"}
    signed_in = client.post(
        "/auth/password",
        headers=alpha,
        json={"email": "alpha-client@example.test", "password": CLIENT_PASSWORD},
    )
    assert signed_in.status_code == 200
    assert "domain=" not in signed_in.headers["set-cookie"].lower()
    assert client.get("/auth/session", headers=alpha).status_code == 200
    denied = client.get("/auth/session", headers=beta)
    assert denied.status_code == 403
    assert denied.json()["detail"] == "Session firm does not match this portal"


@pytest.mark.parametrize("sign_out_headers", [_origin("synthetic-beta"), {}])
def test_sign_out_works_from_any_portal_and_revokes_sessions(portal, sign_out_headers) -> None:
    client, factory, _ = portal
    body = {"email": "alpha-client@example.test", "password": CLIENT_PASSWORD}
    assert (
        client.post("/auth/password", headers=_origin("synthetic-alpha"), json=body).status_code
        == 200
    )
    token = client.cookies.get("ains_session")
    assert token
    # The shared API-host cookie is also sent from another firm's portal: reads are refused...
    for path in ("/auth/session", "/engagements/current"):
        assert client.get(path, headers=_origin("synthetic-beta")).status_code == 403
    # ...but signing out must still work, so a wrong-portal session can always be ended.
    response = client.post("/auth/sign-out", headers=sign_out_headers)
    assert response.status_code == 204
    assert "domain=" not in response.headers["set-cookie"].lower()
    with factory() as db:
        assert all(row.revoked_at is not None for row in db.scalars(select(AuthSession)))
    replay = {**_origin("synthetic-alpha"), "authorization": f"Bearer {token}"}
    assert client.get("/auth/session", headers=replay).status_code == 401


def test_auditor_host_is_auditors_only_and_not_a_firm_slug(portal) -> None:
    client, _, ids = portal
    host = {"origin": f"https://auditor.{BASE}"}
    assert "auditor" in RESERVED_SLUGS
    with pytest.raises(ValueError):
        require_firm_slug("auditor")
    # A client cannot sign in on the auditor host, and no cookie is issued.
    denied = client.post(
        "/auth/password",
        headers=host,
        json={"email": "alpha-client@example.test", "password": CLIENT_PASSWORD},
    )
    assert denied.status_code == 403
    assert "set-cookie" not in denied.headers
    # A client invitation cannot be accepted there either.
    accept = client.post(
        "/auth/invitations/accept",
        headers=host,
        json={"token": ids["invitation_token"], "password": "synthetic-invite-password"},
    )
    assert accept.status_code == 403
    assert "set-cookie" not in accept.headers
    # Auditors can, and CORS allows the auditor origin.
    ok = client.post(
        "/auth/password",
        headers=host,
        json={
            "email": "auditor@example.test",
            "password": AUDITOR_PASSWORD,
            "mfa_code": pyotp.TOTP(MFA_SECRET).now(),
        },
    )
    assert ok.status_code == 200
    assert ok.headers["access-control-allow-origin"] == f"https://auditor.{BASE}"
    assert client.get("/auth/session", headers=host).status_code == 200
    # A client who somehow holds an auditor-host session is refused on later calls.
    client.cookies.clear()
    client.post(
        "/auth/password",
        headers=_origin("synthetic-alpha"),
        json={"email": "alpha-client@example.test", "password": CLIENT_PASSWORD},
    )
    assert client.get("/auth/session", headers=host).status_code == 403
    # The branding route does not treat the auditor host as a firm.
    assert client.get("/tenant/branding", headers=host).status_code == 404
    # A firm origin and the auditor host together are ambiguous and refused.
    both = {**_origin("synthetic-alpha"), "x-forwarded-host": f"auditor.{BASE}"}
    assert client.get("/auth/session", headers=both).status_code == 403


def test_cross_site_post_from_unknown_or_sibling_host_is_refused(portal) -> None:
    client, _, _ = portal
    body = {"email": "alpha-client@example.test", "password": CLIENT_PASSWORD}
    for origin in (
        "https://not-a-firm.kiensolutions.com",
        "https://synthetic-alpha.kiensolutions.com.evil.test",
        "https://api.kiensolutions.com",
        "http://synthetic-alpha.kiensolutions.com",
    ):
        response = client.post("/auth/password", headers={"origin": origin}, json=body)
        assert response.status_code == 403, origin
        assert response.json()["detail"] == "Cross-site request refused"
        assert "set-cookie" not in response.headers
    # A known firm host passes the origin check (and signs in on its own portal).
    ok = client.post("/auth/password", headers=_origin("synthetic-alpha"), json=body)
    assert ok.status_code == 200


def test_cors_keeps_retry_after_exposed(portal) -> None:
    client, _, _ = portal
    response = client.get("/health", headers=_origin("synthetic-alpha"))
    assert response.headers["access-control-expose-headers"] == "Retry-After"


@pytest.mark.parametrize("origin", ["https://[", "https://synthetic-alpha.kiensolutions.com:bad"])
def test_malformed_origins_are_denied_without_server_errors(portal, origin) -> None:
    client, _, _ = portal
    assert allowed_cors_origin(origin, _settings(), frozenset({"synthetic-alpha"})) is None
    response = client.post("/auth/password", headers={"origin": origin}, json={})
    assert response.status_code == 403
    assert "access-control-allow-origin" not in response.headers
    assert "set-cookie" not in response.headers


@pytest.mark.parametrize(
    "method,headers,status",
    [
        ("PUT", "content-type", 200),
        ("DELETE", "authorization", 200),
        ("TRACE", "content-type", 400),
        ("POST", "x-forwarded-host", 400),
    ],
)
def test_preflight_enforces_exact_methods_and_headers(portal, method, headers, status) -> None:
    client, _, _ = portal
    response = client.options(
        "/health",
        headers={
            **_origin("synthetic-alpha"),
            "access-control-request-method": method,
            "access-control-request-headers": headers,
        },
    )
    assert response.status_code == status
    assert ("access-control-allow-origin" in response.headers) == (status == 200)


def test_production_start_accepts_base_domain_without_cors_list() -> None:
    from app.main import enforce_production_safety

    ok = _settings(
        env="production",
        upload_scan_mode="clamav",
        session_cookie_secure=True,
        cors_origins="",
    )
    enforce_production_safety(ok)
    no_domain = _settings(
        env="production",
        upload_scan_mode="clamav",
        session_cookie_secure=True,
        cors_origins="",
        portal_base_domain="",
    )
    with pytest.raises(RuntimeError):
        enforce_production_safety(no_domain)
    bad = _settings(
        env="production",
        upload_scan_mode="clamav",
        session_cookie_secure=True,
        cors_origins="http://localhost:3000",
    )
    with pytest.raises(RuntimeError):
        enforce_production_safety(bad)
