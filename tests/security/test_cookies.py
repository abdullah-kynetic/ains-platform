"""S-02: production session and deletion cookies are host-only and protected."""

from http.cookies import SimpleCookie

import httpx

from app.config import get_settings
from tests.test_backend_api import CLIENT_PASSWORD


def test_production_login_and_signout_cookie_flags(backend):
    client, *_ = backend
    settings = client.app.dependency_overrides[get_settings]()
    settings.env = "production"
    settings.session_cookie_secure = True
    client.base_url = httpx.URL("https://testserver")
    response = client.post(
        "/auth/password",
        json={
            "email": "alpha-client@example.test",
            "password": CLIENT_PASSWORD,
        },
    )
    assert response.status_code == 200
    cookies = SimpleCookie(response.headers["set-cookie"])
    cookie = cookies["ains_session"]
    assert cookie["httponly"] and cookie["secure"]
    assert cookie["samesite"].lower() == "lax"
    assert cookie["path"] == "/" and not cookie["domain"]
    assert int(cookie["max-age"]) == 12 * 3600
    response = client.post("/auth/sign-out")
    assert response.status_code == 204
    removed = SimpleCookie(response.headers["set-cookie"])["ains_session"]
    assert removed["max-age"] == "0" and not removed["domain"]
    assert removed["httponly"] and removed["secure"]
    assert removed["samesite"].lower() == "lax"
