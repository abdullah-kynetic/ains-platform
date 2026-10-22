import hashlib
from urllib.parse import parse_qs

import httpx
import pytest
import respx

from app.egnyte_client import (
    EgnyteAPIError,
    EgnyteAuthError,
    EgnyteClient,
    EgnyteConfigError,
    EgnytePermissionError,
    EgnyteRateLimitError,
    PathNotAllowedError,
    encode_path,
    normalize_domain,
)
from app.egnyte_client.ratelimit import RateLimiter
from tests.conftest import (
    ACCESS,
    BASE,
    CLIENT_ID,
    CLIENT_SECRET,
    PASSWORD,
    REFRESH,
    USERNAME,
    token_json,
)

TOKEN_URL = f"{BASE}/puboauth/token"
USERINFO = {"id": 7, "username": USERNAME, "first_name": "Test", "last_name": "User"}


def form(request: httpx.Request) -> dict[str, str]:
    return {k: v[0] for k, v in parse_qs(request.content.decode()).items()}


# ---------------------------------------------------------------- helpers


def test_encode_path() -> None:
    assert encode_path("/Shared/example?path/$file.txt") == "/Shared/example%3Fpath/%24file.txt"
    assert encode_path("/Shared/AINS-Dev/a b#c.pdf") == "/Shared/AINS-Dev/a%20b%23c.pdf"


@pytest.mark.parametrize(
    "raw", ["quintonsfirm", "QuintonsFirm.egnyte.com", "https://quintonsfirm.egnyte.com/"]
)
def test_normalize_domain(raw: str) -> None:
    assert normalize_domain(raw) == "quintonsfirm"


def test_bad_domain() -> None:
    with pytest.raises(EgnyteConfigError):
        normalize_domain("evil.com/x?y")


# ---------------------------------------------------------------- auth: password flow


@respx.mock
async def test_password_flow_request_shape(make_client) -> None:
    tok = respx.post(TOKEN_URL).mock(return_value=httpx.Response(200, json=token_json()))
    respx.get(f"{BASE}/pubapi/v1/userinfo").mock(return_value=httpx.Response(200, json=USERINFO))
    c = make_client()
    await c.whoami()
    req = tok.calls.last.request
    assert req.headers["content-type"].startswith("application/x-www-form-urlencoded")
    assert form(req) == {
        "grant_type": "password",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "username": USERNAME,
        "password": PASSWORD,
        "scope": "Egnyte.filesystem Egnyte.webhooks",
    }


@respx.mock
async def test_token_cached_and_auth_header(make_client) -> None:
    tok = respx.post(TOKEN_URL).mock(return_value=httpx.Response(200, json=token_json()))
    ui = respx.get(f"{BASE}/pubapi/v1/userinfo").mock(
        return_value=httpx.Response(200, json=USERINFO)
    )
    c = make_client()
    assert (await c.whoami())["username"] == USERNAME
    await c.whoami()
    await c.whoami()
    assert tok.call_count == 1
    assert ui.call_count == 3
    assert ui.calls.last.request.headers["authorization"] == f"Bearer {ACCESS}"


@respx.mock
async def test_expired_token_is_renewed(make_client) -> None:
    now = [1_000_000.0]
    tok = respx.post(TOKEN_URL).mock(
        side_effect=[
            httpx.Response(200, json={**token_json("a1", None), "expires_in": 100}),
            httpx.Response(200, json={**token_json("a2", None), "expires_in": 100}),
        ]
    )
    c = make_client(clock=lambda: now[0])
    assert await c.get_token() == "a1"
    now[0] += 500
    assert await c.get_token() == "a2"
    assert tok.call_count == 2


@respx.mock
async def test_token_401_bad_client_id(make_client) -> None:
    respx.post(TOKEN_URL).mock(
        return_value=httpx.Response(401, json={"message": "No active developer profile"})
    )
    c = make_client()
    with pytest.raises(EgnyteAuthError) as ei:
        await c.whoami()
    msg = str(ei.value)
    assert "Client ID" in msg and "approved" in msg
    assert CLIENT_ID not in msg and PASSWORD not in msg and CLIENT_SECRET not in msg


@respx.mock
async def test_token_403_bad_credentials(make_client) -> None:
    respx.post(TOKEN_URL).mock(
        return_value=httpx.Response(403, text="INVALID_USERNAME_OR_PASSWORD")
    )
    with pytest.raises(EgnyteAuthError) as ei:
        await make_client().whoami()
    assert "EGNYTE_CLIENT_SECRET" in str(ei.value)


async def test_password_flow_requires_secret(make_client) -> None:
    with pytest.raises(EgnyteConfigError, match="EGNYTE_CLIENT_SECRET"):
        await make_client(client_secret="").get_token()


@respx.mock
async def test_token_endpoint_409_throttle_honors_retry_after(make_client, sleeps) -> None:
    respx.post(TOKEN_URL).mock(
        side_effect=[
            httpx.Response(409, headers={"Retry-After": "7"}),
            httpx.Response(200, json=token_json()),
        ]
    )
    assert await make_client().get_token() == ACCESS
    assert 7.0 in sleeps.calls


# ---------------------------------------------------------------- auth: token modes


@respx.mock
async def test_access_token_mode_skips_password_flow(make_client) -> None:
    tok = respx.post(TOKEN_URL)
    ui = respx.get(f"{BASE}/pubapi/v1/userinfo").mock(
        return_value=httpx.Response(200, json=USERINFO)
    )
    c = make_client(access_token="static-token-xyz", username="", password="", client_secret="")
    await c.whoami()
    assert not tok.called
    assert ui.calls.last.request.headers["authorization"] == "Bearer static-token-xyz"


@respx.mock
async def test_access_token_401_refreshes_and_retries(make_client) -> None:
    tok = respx.post(TOKEN_URL).mock(
        return_value=httpx.Response(200, json=token_json("fresh-access", "new-refresh"))
    )
    ui = respx.get(f"{BASE}/pubapi/v1/userinfo").mock(
        side_effect=[httpx.Response(401), httpx.Response(200, json=USERINFO)]
    )
    c = make_client(access_token="stale-token", refresh_token=REFRESH, username="", password="")
    assert (await c.whoami())["id"] == 7
    assert form(tok.calls.last.request) == {
        "grant_type": "refresh_token",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "refresh_token": REFRESH,
    }
    assert ui.calls[0].request.headers["authorization"] == "Bearer stale-token"
    assert ui.calls[1].request.headers["authorization"] == "Bearer fresh-access"
    assert c._refresh_token == "new-refresh"


@respx.mock
async def test_refresh_token_only_mode(make_client) -> None:
    tok = respx.post(TOKEN_URL).mock(return_value=httpx.Response(200, json=token_json()))
    c = make_client(refresh_token=REFRESH, username="", password="")
    assert await c.get_token() == ACCESS
    assert form(tok.calls.last.request)["grant_type"] == "refresh_token"


@respx.mock
async def test_refresh_failure_falls_back_to_password(make_client) -> None:
    respx.post(TOKEN_URL).mock(
        side_effect=[
            httpx.Response(400, json={"message": "Invalid Refresh Token"}),
            httpx.Response(200, json=token_json("pw-access")),
        ]
    )
    c = make_client(refresh_token="dead-refresh")
    assert await c.get_token() == "pw-access"


@respx.mock
async def test_api_401_without_renewal_gives_clear_error(make_client) -> None:
    respx.get(f"{BASE}/pubapi/v1/userinfo").mock(return_value=httpx.Response(401))
    c = make_client(access_token="stale-token", username="", password="", client_secret="")
    with pytest.raises(EgnyteAuthError) as ei:
        await c.whoami()
    assert "expired" in str(ei.value) and "stale-token" not in str(ei.value)


@respx.mock
async def test_api_401_after_renewal_raises(make_client) -> None:
    respx.post(TOKEN_URL).mock(return_value=httpx.Response(200, json=token_json()))
    ui = respx.get(f"{BASE}/pubapi/v1/userinfo").mock(return_value=httpx.Response(401))
    with pytest.raises(EgnyteAuthError):
        await make_client().whoami()
    assert ui.call_count == 2


async def test_no_auth_configured(make_client) -> None:
    c = make_client(client_secret="", username="", password="")
    with pytest.raises(EgnyteAuthError, match="EGNYTE_ACCESS_TOKEN"):
        await c.get_token()


# ---------------------------------------------------------------- errors / retries


@respx.mock
async def test_429_retry_honors_retry_after(make_client, sleeps) -> None:
    route = respx.get(f"{BASE}/pubapi/v1/userinfo").mock(
        side_effect=[
            httpx.Response(429, headers={"Retry-After": "3"}),
            httpx.Response(503),
            httpx.Response(200, json=USERINFO),
        ]
    )
    c = make_client(access_token=ACCESS)
    assert (await c.whoami())["id"] == 7
    assert route.call_count == 3
    assert sleeps.calls[0] == 3.0
    assert sleeps.calls[1] == 2.0  # exponential backoff for attempt 2


@respx.mock
async def test_429_exhausted(make_client) -> None:
    respx.get(f"{BASE}/pubapi/v1/userinfo").mock(return_value=httpx.Response(429))
    with pytest.raises(EgnyteRateLimitError):
        await make_client(access_token=ACCESS, max_attempts=3).whoami()


@respx.mock
async def test_403_permission_message(make_client) -> None:
    respx.get(f"{BASE}/pubapi/v1/fs/Shared/AINS-Dev").mock(
        return_value=httpx.Response(403, json={"errorMessage": "Developer Inactive"})
    )
    with pytest.raises(EgnytePermissionError) as ei:
        await make_client(access_token=ACCESS).list_folder("/Shared/AINS-Dev")
    msg = str(ei.value)
    assert "API access" in msg and "Developer Inactive" in msg


@respx.mock
async def test_error_messages_redact_secrets(make_client) -> None:
    respx.get(f"{BASE}/pubapi/v1/userinfo").mock(
        return_value=httpx.Response(500, json={"message": f"echo {ACCESS}"})
    )
    with pytest.raises(EgnyteAPIError) as ei:
        await make_client(access_token=ACCESS, max_attempts=1).whoami()
    assert ACCESS not in str(ei.value) and "[REDACTED]" in str(ei.value)


async def test_rate_limiter_spaces_calls() -> None:
    now = [0.0]
    slept: list[float] = []

    async def fake_sleep(s: float) -> None:
        slept.append(s)
        now[0] += s

    rl = RateLimiter(2, clock=lambda: now[0], sleep=fake_sleep)
    for _ in range(4):
        await rl.acquire()
    assert slept == [0.5, 0.5, 0.5]


# ---------------------------------------------------------------- path guard before network


async def test_guard_runs_before_any_network(make_client) -> None:
    with respx.mock(assert_all_called=False) as mock:
        await _guard_checks(make_client, mock)


async def _guard_checks(make_client, mock) -> None:
    router = mock.route().mock(return_value=httpx.Response(200, json={}))
    c = make_client()
    bad = "/Shared/Clients/real.pdf"
    for call in (
        lambda: c.list_folder(bad),
        lambda: c.download_file(bad),
        lambda: c.upload_file(bad, b"x"),
        lambda: c.create_folder(bad),
        lambda: c.register_webhook("https://h.example/wh", bad),
        lambda: c.list_folder("/Shared/AINS-Dev/../Clients"),
    ):
        with pytest.raises(PathNotAllowedError):
            await call()
    assert not router.called


# ---------------------------------------------------------------- file system


@respx.mock
async def test_list_folder_parsing(make_client) -> None:
    body = {
        "name": "client 001",
        "path": "/Shared/AINS-Dev/client 001",
        "folder_id": "f1",
        "is_folder": True,
        "total_count": 2,
        "folders": [{"name": "sub", "path": "/Shared/AINS-Dev/client 001/sub", "is_folder": True}],
        "files": [
            {
                "name": "aml-manual.pdf",
                "path": "/Shared/AINS-Dev/client 001/aml-manual.pdf",
                "size": 2048,
                "group_id": "g1",
                "entry_id": "e1",
                "is_folder": False,
            }
        ],
    }
    route = respx.get(f"{BASE}/pubapi/v1/fs/Shared/AINS-Dev/client%20001").mock(
        return_value=httpx.Response(200, json=body)
    )
    listing = await make_client(access_token=ACCESS).list_folder("/Shared/AINS-Dev/client 001")
    assert route.calls.last.request.url.params["list_content"] == "true"
    assert [f.name for f in listing.folders] == ["sub"]
    assert listing.files[0].size == 2048 and listing.files[0].group_id == "g1"
    assert listing.total_count == 2


@respx.mock
async def test_download(make_client) -> None:
    respx.get(f"{BASE}/pubapi/v1/fs-content/Shared/AINS-Dev/a%3Fb.txt").mock(
        return_value=httpx.Response(200, content=b"hello")
    )
    assert await make_client(access_token=ACCESS).download_file("/Shared/AINS-Dev/a?b.txt") == (
        b"hello"
    )


@respx.mock
async def test_upload(make_client, tmp_path) -> None:
    route = respx.post(f"{BASE}/pubapi/v1/fs-content/Shared/AINS-Dev/c1/doc.pdf").mock(
        return_value=httpx.Response(201, json={"checksum": "abc", "group_id": "g9"})
    )
    local = tmp_path / "doc.pdf"
    local.write_bytes(b"%PDF-fake")
    res = await make_client(access_token=ACCESS).upload_file("/Shared/AINS-Dev/c1/doc.pdf", local)
    req = route.calls.last.request
    assert req.headers["content-type"] == "application/octet-stream"
    assert req.headers["x-sha512-checksum"] == hashlib.sha512(b"%PDF-fake").hexdigest()
    assert req.content == b"%PDF-fake"
    assert res["group_id"] == "g9" and res["path"] == "/Shared/AINS-Dev/c1/doc.pdf"


async def test_upload_too_large(make_client, monkeypatch) -> None:
    import app.egnyte_client.client as mod

    monkeypatch.setattr(mod, "SIMPLE_UPLOAD_MAX_BYTES", 3)
    with pytest.raises(ValueError, match="100 MB"):
        await make_client(access_token=ACCESS).upload_file("/Shared/AINS-Dev/x.bin", b"1234")


@respx.mock
async def test_create_folder_and_exists(make_client) -> None:
    route = respx.post(f"{BASE}/pubapi/v1/fs/Shared/AINS-Dev/client-002").mock(
        side_effect=[
            httpx.Response(201, json={"path": "/Shared/AINS-Dev/client-002", "folder_id": "f2"}),
            httpx.Response(409, json={"errorMessage": "Folder already exists"}),
        ]
    )
    c = make_client(access_token=ACCESS)
    assert (await c.create_folder("/Shared/AINS-Dev/client-002"))["folder_id"] == "f2"
    import json

    assert json.loads(route.calls.last.request.content) == {"action": "add_folder"}
    assert (await c.create_folder("/Shared/AINS-Dev/client-002"))["already_existed"] is True


# ---------------------------------------------------------------- webhooks


@respx.mock
async def test_register_webhook_payload(make_client) -> None:
    import json

    route = respx.post(f"{BASE}/pubapi/v1/webhooks").mock(
        return_value=httpx.Response(
            201, json={"webhookId": "w1", "expires": 2100000000, "status": "enabled"}
        )
    )
    c = make_client(access_token=ACCESS)
    res = await c.register_webhook(
        "https://ains.example/hooks/egnyte",
        ["/Shared/AINS-Dev/c1", "/Shared/AINS-Dev/c2/"],
        auth_header="Bearer hook-secret",
    )
    assert res["webhookId"] == "w1"
    assert json.loads(route.calls.last.request.content) == {
        "url": "https://ains.example/hooks/egnyte",
        "eventType": ["fs:add_file"],
        "path": "/Shared/AINS-Dev/c1,/Shared/AINS-Dev/c2",
        "authHeader": "Bearer hook-secret",
    }


async def test_webhook_requires_https(make_client) -> None:
    with pytest.raises(ValueError, match="HTTPS"):
        await make_client(access_token=ACCESS).register_webhook(
            "http://x.example", "/Shared/AINS-Dev"
        )


def test_repr_hides_secrets(make_client) -> None:
    c = make_client(access_token=ACCESS, refresh_token=REFRESH)
    r = repr(c)
    assert all(s not in r for s in (ACCESS, REFRESH, CLIENT_SECRET, PASSWORD, CLIENT_ID))
    assert isinstance(c, EgnyteClient)
