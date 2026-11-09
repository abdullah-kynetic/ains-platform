"""Cross-site state-changing requests are refused; the portal's own origin is allowed."""

from tests.test_backend_api import backend, sign_in_client  # noqa: F401

PORTAL = "http://localhost:3000"  # the configured portal origin in the test app
EVIL = "https://evil.example.test"


def upload(client, ids, **headers):
    return client.post(
        f"/engagements/{ids['engagement_a']}/items/{ids['item_a']}/documents",
        files={"file": ("synthetic.txt", b"synthetic replacement")},
        headers=headers,
    )


def test_cross_site_multipart_upload_is_rejected_and_stores_nothing(backend):  # noqa: F811
    client, _factory, ids, ingestor, _sender = backend
    sign_in_client(client)  # the browser would send this cookie on a cross-site form post
    response = upload(client, ids, Origin=EVIL)
    assert response.status_code == 403
    assert ingestor.calls == 0


def test_same_origin_upload_is_allowed(backend):  # noqa: F811
    client, _factory, ids, ingestor, _sender = backend
    sign_in_client(client)
    assert upload(client, ids, Origin=PORTAL).status_code == 201
    assert ingestor.calls == 1


def test_sibling_host_and_lookalike_origins_are_rejected(backend):  # noqa: F811
    client, _factory, ids, ingestor, _sender = backend
    sign_in_client(client)
    for origin in (
        "https://other.kiensolutions.com",  # a sibling host is not trusted by wildcard
        "http://localhost:3000.evil.example.test",
        "http://localhost:3001",
        "null",
    ):
        assert upload(client, ids, Origin=origin).status_code == 403, origin
    assert ingestor.calls == 0


def test_referer_is_checked_when_origin_is_absent(backend):  # noqa: F811
    client, _factory, ids, ingestor, _sender = backend
    sign_in_client(client)
    assert upload(client, ids, Referer=f"{EVIL}/page").status_code == 403
    assert upload(client, ids, Referer=f"{PORTAL}/upload").status_code == 201


def test_sign_in_and_other_posts_are_checked_too(backend):  # noqa: F811
    client, *_ = backend
    response = client.post(
        "/auth/password",
        json={"email": "alpha-client@example.test", "password": "x"},
        headers={"Origin": EVIL},
    )
    assert response.status_code == 403


def test_reads_and_header_less_clients_are_not_blocked(backend):  # noqa: F811
    client, _factory, ids, *_ = backend
    sign_in_client(client)  # no Origin header: scripts and tests are not browser form posts
    assert client.get("/auth/session", headers={"Origin": EVIL}).status_code == 200


# --- Direct middleware tests: every unsafe method, "null" and unparsable values -----------------

import pytest  # noqa: E402
from starlette.applications import Starlette  # noqa: E402
from starlette.responses import PlainTextResponse  # noqa: E402
from starlette.routing import Route  # noqa: E402
from starlette.testclient import TestClient  # noqa: E402

from app.origin_check import OriginCheckMiddleware  # noqa: E402


def _client() -> TestClient:
    async def ok(request):
        return PlainTextResponse("ok")

    app = Starlette(
        routes=[Route("/x", ok, methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])]
    )
    app.add_middleware(
        OriginCheckMiddleware, allowed_origins=[PORTAL, "https://acme.example.test/"]
    )
    return TestClient(app)


@pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE"])
def test_every_unsafe_method_is_checked(method):
    client = _client()
    assert client.request(method, "/x", headers={"Origin": EVIL}).status_code == 403
    assert client.request(method, "/x", headers={"Origin": PORTAL}).status_code == 200
    assert client.request(method, "/x", headers={"Referer": f"{EVIL}/p"}).status_code == 403


@pytest.mark.parametrize(
    "value", ["null", "", "not a url", "//localhost:3000", "localhost:3000", "https://"]
)
def test_null_and_unparsable_origins_are_rejected(value):
    assert _client().post("/x", headers={"Origin": value}).status_code == 403


def test_allowed_list_entries_match_exactly_ignoring_case_and_trailing_slash():
    client = _client()
    assert client.post("/x", headers={"Origin": "https://ACME.example.test"}).status_code == 200
    assert (
        client.post("/x", headers={"Origin": "https://acme.example.test:8443"}).status_code == 403
    )
    assert client.post("/x", headers={"Origin": "http://acme.example.test"}).status_code == 403


@pytest.mark.parametrize("method", ["GET", "OPTIONS"])
def test_safe_methods_are_not_checked(method):
    assert _client().request(method, "/x", headers={"Origin": EVIL}).status_code == 200
