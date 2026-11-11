"""Step 4: the API sends security headers on every kind of response."""

from tests.test_backend_api import backend, sign_in_auditor  # noqa: F401

REQUIRED = {
    "strict-transport-security",
    "x-frame-options",
    "x-content-type-options",
    "referrer-policy",
    "permissions-policy",
    "content-security-policy",
}


def _check(response):
    assert REQUIRED <= {k.lower() for k in response.headers}, dict(response.headers)
    assert response.headers["x-frame-options"] == "DENY"
    assert "max-age=" in response.headers["strict-transport-security"]
    assert "frame-ancestors 'none'" in response.headers["content-security-policy"]
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["referrer-policy"] == "no-referrer"


def test_headers_on_success_error_and_authenticated_responses(backend):  # noqa: F811
    client, *_ = backend
    _check(client.get("/health"))
    _check(client.get("/auditor/engagements"))  # 401
    _check(client.get("/no-such-route"))  # 404
    sign_in_auditor(client)
    ok = client.get("/auditor/engagements")
    assert ok.status_code == 200
    _check(ok)


def test_docs_pages_keep_the_other_headers_but_not_the_api_csp(backend):  # noqa: F811
    client, *_ = backend
    docs = client.get("/docs")
    assert docs.headers["x-frame-options"] == "DENY"
    assert "content-security-policy" not in {k.lower() for k in docs.headers}
