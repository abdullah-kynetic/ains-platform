"""Async Egnyte Public API client (httpx + tenacity).

Docs this client is built against:
- Auth (password, refresh flows; 30-day tokens; userinfo):
  https://developers.egnyte.com/docs/read/Public_API_Authentication
  https://developers.egnyte.com/integration/cfs/api-docs/authentication
- File System (list, create folder, upload, download; path encoding; 100 MB simple-upload limit):
  https://developers.egnyte.com/docs/read/File_System_Management_API_Documentation
- Webhooks (POST /pubapi/v1/webhooks with url, eventType[], path, authHeader):
  https://developers.egnyte.com/docs/read/Webhooks
- Rate limits (2 calls/sec, 1,000 calls/day per token; internal-app token endpoint
  10 requests/user/hour, throttled with 409 + Retry-After):
  https://developers.egnyte.com/docs/read/Best_Practices

Every path-based method runs ``guard_path`` against the configured root *before*
any network call. Credentials and tokens are never logged, printed, or put in errors.
"""

from __future__ import annotations

import asyncio
import hashlib
import os
import re
import time
from collections.abc import Awaitable, Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

import httpx
from pydantic import BaseModel, ConfigDict, Field
from tenacity import AsyncRetrying, RetryCallState, retry_if_exception_type, stop_after_attempt

from .errors import (
    EgnyteAPIError,
    EgnyteAuthError,
    EgnyteConfigError,
    EgnyteError,
    EgnyteNotFoundError,
    EgnytePermissionError,
    EgnyteRateLimitError,
)
from .paths import DEFAULT_DEV_ROOT, encode_path, guard_path
from .ratelimit import RateLimiter

if TYPE_CHECKING:
    from app.config import Settings

DEFAULT_SCOPES = "Egnyte.filesystem Egnyte.webhooks"
MAX_REQUESTS_PER_SECOND = 2
SIMPLE_UPLOAD_MAX_BYTES = 100 * 1024 * 1024  # larger files need the chunked endpoint
RETRYABLE_STATUS = {429, 500, 502, 503, 504}
MAX_RETRY_AFTER_SECONDS = 120.0


# --------------------------------------------------------------------------- models


class _Model(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)


class FolderEntry(_Model):
    name: str
    path: str
    folder_id: str | None = None
    is_folder: bool = True


class FileEntry(_Model):
    name: str
    path: str
    size: int | None = None
    checksum: str | None = None
    entry_id: str | None = None
    group_id: str | None = None
    last_modified: str | None = None
    uploaded_by: str | None = None
    is_folder: bool = False


class FolderListing(_Model):
    name: str | None = None
    path: str
    folder_id: str | None = None
    is_folder: bool = True
    total_count: int | None = None
    count: int | None = None
    offset: int | None = None
    folders: list[FolderEntry] = Field(default_factory=list)
    files: list[FileEntry] = Field(default_factory=list)


@dataclass
class TokenSet:
    access_token: str
    refresh_token: str | None = None
    expires_at: float | None = None  # epoch seconds; None = unknown (static token)


# --------------------------------------------------------------------------- helpers


class _Retryable(Exception):
    def __init__(self, response: httpx.Response | None = None, retry_after: float | None = None):
        super().__init__("retryable")
        self.response = response
        self.retry_after = retry_after


def _parse_retry_after(resp: httpx.Response) -> float | None:
    value = resp.headers.get("Retry-After")
    if not value:
        return None
    try:
        return max(0.0, min(float(value), MAX_RETRY_AFTER_SECONDS))
    except ValueError:
        return None


def _wait(state: RetryCallState) -> float:
    exc = state.outcome.exception() if state.outcome else None
    if isinstance(exc, _Retryable) and exc.retry_after is not None:
        return exc.retry_after
    return float(min(2 ** (state.attempt_number - 1), 30))


def normalize_domain(domain: str) -> str:
    """Accept 'firm', 'firm.egnyte.com', or 'https://firm.egnyte.com/' and return 'firm'."""
    d = (domain or "").strip().lower()
    d = re.sub(r"^https?://", "", d).split("/")[0]
    d = d.removesuffix(".egnyte.com")
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", d):
        raise EgnyteConfigError(
            "EGNYTE_DOMAIN must be your Egnyte subdomain only, e.g. 'quintonsfirm'"
        )
    return d


# --------------------------------------------------------------------------- client


class EgnyteClient:
    """Thin async client for the Egnyte Public API.

    Auth modes (first that applies):
    1. ``access_token`` given: used as-is. On 401 it is renewed with the refresh
       token (if any), else the password flow (if credentials are set).
    2. ``refresh_token`` given: refresh-token flow to mint an access token.
    3. Password flow (Internal app): client_id, client_secret, username, password.
    Tokens are cached in memory only.
    """

    def __init__(
        self,
        domain: str,
        client_id: str,
        client_secret: str = "",
        username: str = "",
        password: str = "",
        *,
        access_token: str = "",
        refresh_token: str = "",
        scopes: str = DEFAULT_SCOPES,
        root: str = DEFAULT_DEV_ROOT,
        max_per_second: float = MAX_REQUESTS_PER_SECOND,
        max_attempts: int = 5,
        http_client: httpx.AsyncClient | None = None,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self.domain = normalize_domain(domain)
        self.base_url = f"https://{self.domain}.egnyte.com"
        self.root = root
        self.scopes = scopes
        self._client_id = client_id
        self._client_secret = client_secret
        self._username = username
        self._password = password
        self._refresh_token = refresh_token or None
        self._token: TokenSet | None = (
            TokenSet(access_token, self._refresh_token) if access_token else None
        )
        self._http = http_client or httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=10.0))
        self._owns_http = http_client is None
        self._sleep = sleep
        self._clock = clock
        self._limiter = RateLimiter(max_per_second, sleep=sleep)
        self._max_attempts = max_attempts
        self._token_lock = asyncio.Lock()

    @classmethod
    def from_settings(cls, settings: Settings, **kwargs: Any) -> EgnyteClient:
        if not settings.egnyte_domain:
            raise EgnyteConfigError("EGNYTE_DOMAIN is not set")
        return cls(
            domain=settings.egnyte_domain,
            client_id=settings.egnyte_api_key.get_secret_value(),
            client_secret=settings.egnyte_client_secret.get_secret_value(),
            username=settings.egnyte_username,
            password=settings.egnyte_password.get_secret_value(),
            access_token=settings.egnyte_access_token.get_secret_value(),
            refresh_token=settings.egnyte_refresh_token.get_secret_value(),
            scopes=settings.egnyte_scopes,
            root=settings.egnyte_dev_root,
            **kwargs,
        )

    def __repr__(self) -> str:  # never expose credentials
        return f"EgnyteClient(domain={self.domain!r}, root={self.root!r})"

    async def __aenter__(self) -> EgnyteClient:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        if self._owns_http:
            await self._http.aclose()

    # ------------------------------------------------------------------ redaction

    def _secrets(self) -> list[str]:
        vals = [self._client_id, self._client_secret, self._password, self._refresh_token]
        if self._token:
            vals += [self._token.access_token, self._token.refresh_token]
        return [v for v in vals if v and len(v) >= 4]

    def _redact(self, text: str) -> str:
        for s in self._secrets():
            text = text.replace(s, "[REDACTED]")
        return text

    def _egnyte_message(self, resp: httpx.Response) -> str:
        msg = ""
        try:
            body = resp.json()
        except ValueError:
            body = None
        if isinstance(body, dict):
            errors = body.get("Errors") or body.get("errors")
            if isinstance(errors, list) and errors and isinstance(errors[0], dict):
                msg = str(errors[0].get("description") or errors[0].get("message") or "")
            msg = msg or str(
                body.get("message")
                or body.get("errorMessage")
                or body.get("error_description")
                or body.get("error")
                or body.get("code")
                or ""
            )
        elif resp.text and len(resp.text) < 300 and "<" not in resp.text:
            msg = resp.text.strip()
        msg = self._redact(msg)[:300]
        return f" (Egnyte says: {msg})" if msg else ""

    # ------------------------------------------------------------------ transport

    async def _send(
        self, method: str, url: str, *, token_endpoint: bool = False, **kwargs: Any
    ) -> httpx.Response:
        """Rate-limited request with retries on 429/5xx (and token-endpoint 409)."""

        async def attempt() -> httpx.Response:
            await self._limiter.acquire()
            try:
                resp = await self._http.request(method, url, **kwargs)
            except httpx.TransportError as e:
                raise _Retryable() from e
            if resp.status_code in RETRYABLE_STATUS or (token_endpoint and resp.status_code == 409):
                raise _Retryable(resp, _parse_retry_after(resp))
            mashery = resp.headers.get("X-Mashery-Error-Code", "")
            if resp.status_code == 403 and "OVER_QPS" in mashery:
                raise _Retryable(resp, _parse_retry_after(resp) or 1.0)
            return resp

        try:
            async for att in AsyncRetrying(
                retry=retry_if_exception_type(_Retryable),
                stop=stop_after_attempt(self._max_attempts),
                wait=_wait,
                sleep=self._sleep,
                reraise=True,
            ):
                with att:
                    return await attempt()
        except _Retryable as e:
            resp = e.response
            if resp is None:
                raise EgnyteAPIError(
                    f"Could not reach {self.base_url} after {self._max_attempts} attempts"
                ) from None
            if resp.status_code in (429, 409, 403):
                hint = (
                    " Internal apps may request at most 10 tokens per user per hour; "
                    "reuse a token (see `get-token`)."
                    if token_endpoint
                    else " Egnyte allows 2 calls/sec and 1,000 calls/day per token by default."
                )
                raise EgnyteRateLimitError(
                    f"Egnyte rate limit still hit after {self._max_attempts} attempts.{hint}",
                    resp.status_code,
                ) from None
            raise EgnyteAPIError(
                f"Egnyte server error {resp.status_code} after {self._max_attempts} attempts"
                f"{self._egnyte_message(resp)}",
                resp.status_code,
            ) from None
        raise AssertionError("unreachable")  # pragma: no cover

    # ------------------------------------------------------------------ auth

    def _require(self, *pairs: tuple[str, str]) -> None:
        missing = [name for name, val in pairs if not val]
        if missing:
            raise EgnyteConfigError(f"Missing required setting(s): {', '.join(missing)}")

    async def _token_request(self, data: dict[str, str]) -> TokenSet:
        """POST /puboauth/token (form-encoded) and parse the token response."""
        resp = await self._send(
            "POST", f"{self.base_url}/puboauth/token", data=data, token_endpoint=True
        )
        if resp.status_code == 200:
            body = resp.json()
            expires_in = body.get("expires_in")
            return TokenSet(
                access_token=body["access_token"],
                refresh_token=body.get("refresh_token"),
                expires_at=(self._clock() + float(expires_in)) if expires_in else None,
            )
        detail = self._egnyte_message(resp)
        if resp.status_code == 401:
            raise EgnyteAuthError(
                "Egnyte rejected the Client ID (EGNYTE_API_KEY): no active developer profile. "
                "Check the key is correct and that it has been approved/activated for this "
                f"domain.{detail}",
                401,
            )
        if resp.status_code == 403:
            raise EgnyteAuthError(
                "Egnyte rejected the credentials: wrong EGNYTE_USERNAME/EGNYTE_PASSWORD or a "
                "missing/incorrect EGNYTE_CLIENT_SECRET. If they are correct, confirm the "
                f"Egnyte plan includes API access.{detail}",
                403,
            )
        raise EgnyteAuthError(
            f"Egnyte token request failed with HTTP {resp.status_code}.{detail}",
            resp.status_code,
        )

    async def password_grant(self) -> TokenSet:
        """Resource Owner Password Credentials flow (Internal apps).

        POST https://{domain}.egnyte.com/puboauth/token, form-encoded:
        client_id, client_secret, username, password, grant_type=password, scope.
        """
        self._require(
            ("EGNYTE_API_KEY (Client ID)", self._client_id),
            ("EGNYTE_CLIENT_SECRET", self._client_secret),
            ("EGNYTE_USERNAME", self._username),
            ("EGNYTE_PASSWORD", self._password),
        )
        data = {
            "grant_type": "password",
            "client_id": self._client_id,
            "client_secret": self._client_secret,
            "username": self._username,
            "password": self._password,
        }
        if self.scopes:
            data["scope"] = self.scopes
        tok = await self._token_request(data)
        self._token = tok
        self._refresh_token = tok.refresh_token or self._refresh_token
        return tok

    async def refresh_grant(self) -> TokenSet:
        """Refresh Token flow: grant_type=refresh_token with client_id + client_secret."""
        self._require(
            ("EGNYTE_API_KEY (Client ID)", self._client_id),
            ("EGNYTE_CLIENT_SECRET", self._client_secret),
            ("EGNYTE_REFRESH_TOKEN", self._refresh_token or ""),
        )
        tok = await self._token_request(
            {
                "grant_type": "refresh_token",
                "client_id": self._client_id,
                "client_secret": self._client_secret,
                "refresh_token": self._refresh_token or "",
            }
        )
        tok.refresh_token = tok.refresh_token or self._refresh_token
        self._token = tok
        self._refresh_token = tok.refresh_token
        return tok

    def _has_password_creds(self) -> bool:
        return bool(self._client_id and self._client_secret and self._username and self._password)

    def _can_refresh(self) -> bool:
        return bool(self._client_id and self._client_secret and self._refresh_token)

    async def _renew(self) -> TokenSet:
        if self._can_refresh():
            try:
                return await self.refresh_grant()
            except EgnyteAuthError:
                if not self._has_password_creds():
                    raise
        if self._has_password_creds() or self._username or self._password:
            return await self.password_grant()  # raises a clear error if a setting is missing
        raise EgnyteAuthError(
            "No way to obtain an Egnyte token: set EGNYTE_ACCESS_TOKEN, or "
            "EGNYTE_REFRESH_TOKEN + EGNYTE_CLIENT_SECRET, or EGNYTE_USERNAME + "
            "EGNYTE_PASSWORD + EGNYTE_CLIENT_SECRET."
        )

    async def get_token(self) -> str:
        """Return a valid access token, minting one if needed. Cached in memory only."""
        async with self._token_lock:
            tok = self._token
            if tok and (tok.expires_at is None or tok.expires_at - 60 > self._clock()):
                return tok.access_token
            self._token = None
            return (await self._renew()).access_token

    async def _api(self, method: str, path_url: str, **kwargs: Any) -> httpx.Response:
        """Authenticated API call. On 401, renew the token once and retry."""
        url = f"{self.base_url}{path_url}"
        renewed = False
        while True:
            token = await self.get_token()
            headers = {**kwargs.pop("headers", {}), "Authorization": f"Bearer {token}"}
            resp = await self._send(method, url, headers=headers, **kwargs)
            kwargs["headers"] = {k: v for k, v in headers.items() if k != "Authorization"}
            if (
                resp.status_code == 401
                and not renewed
                and (self._can_refresh() or self._has_password_creds())
            ):
                async with self._token_lock:
                    if self._token and self._token.access_token == token:
                        self._token = None
                        await self._renew()
                renewed = True
                continue
            self._raise_for_status(resp)
            return resp

    def _raise_for_status(self, resp: httpx.Response) -> None:
        code = resp.status_code
        if 200 <= code < 300:
            return
        detail = self._egnyte_message(resp)
        if code == 401:
            raise EgnyteAuthError(
                "Egnyte access token is invalid, expired, or revoked (tokens last 30 days and "
                "are revoked on password change). Renew it with `get-token` or set "
                f"EGNYTE_REFRESH_TOKEN.{detail}",
                401,
            )
        if code == 403:
            if "OVER_RATE" in resp.headers.get("X-Mashery-Error-Code", ""):
                raise EgnyteRateLimitError(
                    f"Egnyte daily API quota exhausted for this token.{detail}", 403
                )
            raise EgnytePermissionError(
                "Egnyte refused the request (403): the user lacks permission on this path, the "
                "token is missing a required scope (EGNYTE_SCOPES), or the Egnyte plan/key "
                f"does not allow API access.{detail}",
                403,
            )
        if code == 404:
            raise EgnyteNotFoundError(f"Not found in Egnyte.{detail}", 404)
        raise EgnyteAPIError(f"Egnyte returned HTTP {code}.{detail}", code)

    # ------------------------------------------------------------------ API

    def _guard(self, path: str) -> str:
        return guard_path(path, self.root)

    async def whoami(self) -> dict[str, Any]:
        """GET /pubapi/v1/userinfo: id, username, first_name, last_name of the token's user."""
        return (await self._api("GET", "/pubapi/v1/userinfo")).json()

    async def list_folder(
        self, path: str, *, count: int | None = None, offset: int = 0
    ) -> FolderListing:
        """GET /pubapi/v1/fs/{path}?list_content=true: folder metadata, subfolders, files."""
        p = self._guard(path)
        params: dict[str, Any] = {"list_content": "true"}
        if count is not None:
            params["count"] = count
            params["offset"] = offset
        resp = await self._api("GET", f"/pubapi/v1/fs{encode_path(p)}", params=params)
        body = resp.json()
        body.setdefault("path", p)
        return FolderListing.model_validate(body)

    async def create_folder(self, path: str, *, exist_ok: bool = True) -> dict[str, Any]:
        """POST /pubapi/v1/fs/{path} with {"action": "add_folder"}.

        Egnyte returns 409 if it already exists; with ``exist_ok`` that is not an error.
        """
        p = self._guard(path)
        try:
            resp = await self._api(
                "POST", f"/pubapi/v1/fs{encode_path(p)}", json={"action": "add_folder"}
            )
        except EgnyteAPIError as e:
            if exist_ok and e.status_code == 409:
                return {"path": p, "already_existed": True}
            raise
        return resp.json() if resp.content else {"path": p}

    async def upload_file(self, path: str, data: bytes | os.PathLike[str] | str) -> dict[str, Any]:
        """POST /pubapi/v1/fs-content/{path}: create or overwrite a file (new version).

        ``data`` is bytes or a local file path. Sent as multipart/form-data (field "file")
        with an X-Sha512-Checksum header for integrity. Simple upload is limited to 100 MB;
        larger files need the chunked endpoint (/pubapi/v1/fs-content-chunked), which is
        not implemented yet.
        """
        p = self._guard(path)
        if p.rstrip("/").casefold() == self.root.rstrip("/").casefold():
            raise ValueError("Upload path must include a file name under the root")
        if isinstance(data, bytes | bytearray):
            content = bytes(data)
        else:
            local = Path(data)
            if local.stat().st_size > SIMPLE_UPLOAD_MAX_BYTES:
                raise ValueError("File exceeds 100 MB; chunked upload is not implemented yet")
            content = local.read_bytes()
        if len(content) > SIMPLE_UPLOAD_MAX_BYTES:
            raise ValueError("File exceeds 100 MB; chunked upload is not implemented yet")
        name = p.rsplit("/", 1)[-1]
        resp = await self._api(
            "POST",
            f"/pubapi/v1/fs-content{encode_path(p)}",
            files={"file": (name, content)},
            headers={"X-Sha512-Checksum": hashlib.sha512(content).hexdigest()},
        )
        try:
            body = resp.json() if resp.content else {}
        except ValueError:
            body = {}
        body.setdefault("path", p)
        return body

    async def download_file(self, path: str) -> bytes:
        """GET /pubapi/v1/fs-content/{path}: file bytes (current version)."""
        p = self._guard(path)
        resp = await self._api("GET", f"/pubapi/v1/fs-content{encode_path(p)}")
        return resp.content

    async def register_webhook(
        self,
        url: str,
        path_filter: str | Iterable[str],
        event_types: Iterable[str] = ("fs:add_file",),
        *,
        auth_header: str | None = None,
    ) -> dict[str, Any]:
        """POST /pubapi/v1/webhooks (needs the Egnyte.webhooks scope).

        Body: {"url", "eventType": [...], "path": "<comma-separated paths>", "authHeader"}.
        Egnyte sends ``authHeader`` back as the ``authorization`` header on each delivery;
        verify it. Response: {"webhookId", "expires", "status"}. Max 100 paths.
        """
        if not url.startswith("https://"):
            raise ValueError("Webhook url must be HTTPS (Egnyte requires a CA-signed cert)")
        paths = [path_filter] if isinstance(path_filter, str) else list(path_filter)
        if not paths or len(paths) > 100:
            raise ValueError("Provide 1 to 100 paths to monitor")
        guarded = []
        for p in paths:
            if "," in p:
                raise ValueError("Paths in a webhook filter may not contain commas")
            guarded.append(self._guard(p))
        events = list(event_types)
        if not events:
            raise ValueError("Provide at least one event type")
        payload: dict[str, Any] = {"url": url, "eventType": events, "path": ",".join(guarded)}
        if auth_header:
            payload["authHeader"] = auth_header
        return (await self._api("POST", "/pubapi/v1/webhooks", json=payload)).json()


__all__ = [
    "DEFAULT_SCOPES",
    "MAX_REQUESTS_PER_SECOND",
    "SIMPLE_UPLOAD_MAX_BYTES",
    "EgnyteClient",
    "EgnyteError",
    "FileEntry",
    "FolderEntry",
    "FolderListing",
    "TokenSet",
    "normalize_domain",
]
