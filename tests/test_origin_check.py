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
