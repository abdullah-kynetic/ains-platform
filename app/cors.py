"""Credentialed CORS allowlist for the shared API.

Allowed origins are the apex, ``www``, ``auditor``, exact ``CORS_ORIGINS`` entries (local
development), and ``https://<slug>.<base>`` only when ``<slug>`` is a real firm
label. Unknown subdomains are not reflected. ``*`` is never sent.
"""

from __future__ import annotations

from urllib.parse import urlsplit

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.config import Settings, get_settings
from app.tenancy import (
    AUDITOR_LABEL,
    RESERVED_SLUGS,
    SLUG_RE,
    dev_localhost_portals_enabled,
    known_portal_slugs,
    localhost_portal_kind,
)

ALLOW_METHODS = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
ALLOW_HEADERS = "Authorization, Content-Type"
# The web app reads Retry-After to tell a locked-out user how long to wait.
EXPOSE_HEADERS = "Retry-After"


def _dev_localhost_origin(candidate: str, settings: Settings, slugs: frozenset[str]) -> str | None:
    """Echo ``http://<known-slug>.localhost[:port]`` only while dev portals are enabled."""
    parsed = urlsplit(candidate)
    if (
        parsed.scheme != "http"
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.path not in {"", "/"}
        or parsed.query
        or parsed.fragment
    ):
        return None
    host = parsed.hostname.lower().rstrip(".")
    if not host.endswith(".localhost"):
        return None
    if not dev_localhost_portals_enabled(settings):
        return None
    kind, label = localhost_portal_kind(host)
    if kind != "firm" or not label or label not in slugs:
        return None
    if parsed.port:
        echoed = f"http://{label}.localhost:{parsed.port}"
    else:
        echoed = f"http://{label}.localhost"
    return echoed if echoed == candidate else None


def _is_localhost_portal_origin(candidate: str) -> bool:
    parsed = urlsplit(candidate)
    host = (parsed.hostname or "").lower().rstrip(".")
    return parsed.scheme == "http" and host.endswith(".localhost")


def allowed_cors_origin(origin: str, settings: Settings, slugs: frozenset[str]) -> str | None:
    """Return the origin to echo, or None when the request origin is not allowlisted."""
    try:
        return _allowed_cors_origin(origin, settings, slugs)
    except ValueError:
        # Malformed URL authority/port is untrusted input, not an application error.
        return None


def _allowed_cors_origin(origin: str, settings: Settings, slugs: frozenset[str]) -> str | None:
    candidate = origin.strip()
    if not candidate or any(char in candidate for char in "\r\n "):
        return None
    if _is_localhost_portal_origin(candidate):
        # Checked before CORS_ORIGINS so production cannot list these origins back on.
        return _dev_localhost_origin(candidate, settings, slugs)
    extras = set(settings.parsed_cors_origins())
    if candidate in extras:
        return candidate

    parsed = urlsplit(candidate)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.port
        or parsed.username
        or parsed.password
        or parsed.path not in {"", "/"}
        or parsed.query
        or parsed.fragment
    ):
        return None
    host = parsed.hostname.lower().rstrip(".")
    base = settings.portal_base_domain
    if not base:
        return None
    if host in {base, f"www.{base}", f"{AUDITOR_LABEL}.{base}"}:
        echoed = f"https://{host}"
        return echoed if echoed == candidate else None
    suffix = f".{base}"
    if not host.endswith(suffix):
        return None
    label = host[: -len(suffix)]
    if label in RESERVED_SLUGS or SLUG_RE.fullmatch(label) is None or label not in slugs:
        return None
    echoed = f"https://{label}.{base}"
    return echoed if echoed == candidate else None


def _settings_for(scope: Scope) -> Settings:
    app = scope.get("app")
    override = getattr(app, "dependency_overrides", {}).get(get_settings)
    if override is not None:
        return override()
    return get_settings()


def _slugs_for(scope: Scope) -> frozenset[str]:
    app = scope.get("app")
    state = getattr(app, "state", None)
    override = getattr(state, "portal_slugs", None) if state is not None else None
    return known_portal_slugs(override)


def _header(scope: Scope, name: bytes) -> str | None:
    for key, value in scope.get("headers", []):
        if key == name:
            return value.decode("latin-1")
    return None


def _cors_headers(origin: str, *, preflight: bool) -> list[tuple[bytes, bytes]]:
    headers = [
        (b"access-control-allow-origin", origin.encode("latin-1")),
        (b"access-control-allow-credentials", b"true"),
        (b"vary", b"Origin"),
    ]
    if not preflight:
        headers.append((b"access-control-expose-headers", EXPOSE_HEADERS.encode("latin-1")))
    if preflight:
        headers.extend(
            [
                (b"access-control-allow-methods", ALLOW_METHODS.encode("latin-1")),
                (b"access-control-allow-headers", ALLOW_HEADERS.encode("latin-1")),
                (b"access-control-max-age", b"600"),
            ]
        )
    return headers


class PortalCORSMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        origin = _header(scope, b"origin")
        if not origin:
            await self.app(scope, receive, send)
            return
        allowed = allowed_cors_origin(origin, _settings_for(scope), _slugs_for(scope))
        request_method = _header(scope, b"access-control-request-method")
        preflight = scope["method"] == "OPTIONS" and bool(request_method)
        if preflight:
            requested_headers = _header(scope, b"access-control-request-headers") or ""
            headers_allowed = all(
                name.strip().lower() in {"authorization", "content-type"}
                for name in requested_headers.split(",")
                if name.strip()
            )
            permitted = allowed and request_method in ALLOW_METHODS.split(", ") and headers_allowed
            status = 200 if permitted else 400
            allowed = allowed if permitted else None
            headers = _cors_headers(allowed, preflight=True) if allowed else [(b"vary", b"Origin")]
            await send({"type": "http.response.start", "status": status, "headers": headers})
            await send({"type": "http.response.body", "body": b""})
            return
        if not allowed:
            await self.app(scope, receive, send)
            return

        async def send_allowed(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.extend(_cors_headers(allowed, preflight=False))
                message = {**message, "headers": headers}
            await send(message)

        await self.app(scope, receive, send_allowed)


def portal_origin_allowed(scope: Scope, origin: str) -> bool:
    """Same allowlist as CORS, for the state-changing request origin check."""
    return allowed_cors_origin(origin, _settings_for(scope), _slugs_for(scope)) is not None
