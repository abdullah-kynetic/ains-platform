"""Reject cross-site state-changing requests (CSRF defence in depth beside SameSite=Lax).

A browser always sends Origin on a cross-site POST. If Origin (or, failing that, Referer) is present
on POST/PUT/PATCH/DELETE it must be one of the configured portal origins, compared exactly: no
wildcard over sibling hosts, so another site under the same parent domain cannot submit forms (for
example multipart uploads, which are "simple" requests that skip the CORS preflight).
Requests with neither header are not browser form posts and pass; they carry no ambient cookie risk.
"""

from collections.abc import Callable
from urllib.parse import urlsplit

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def _origin_of(value: str) -> str | None:
    parts = urlsplit(value)
    if not parts.scheme or not parts.netloc:
        return None
    return f"{parts.scheme}://{parts.netloc}".lower()


class OriginCheckMiddleware:
    def __init__(
        self,
        app: ASGIApp,
        *,
        allowed_origins: list[str],
        extra_allowed: Callable[[Scope, str], bool] | None = None,
    ) -> None:
        self.app = app
        # Optional exact-match lookup, e.g. the firm portal hosts read from the database.
        self.extra_allowed = extra_allowed
        self.allowed = {origin.rstrip("/").lower() for origin in allowed_origins}

    def _allowed(self, scope: Scope, origin: str) -> bool:
        if origin in self.allowed:
            return True
        return self.extra_allowed is not None and self.extra_allowed(scope, origin)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["method"] not in UNSAFE_METHODS:
            await self.app(scope, receive, send)
            return
        headers = {k.decode("latin-1").lower(): v.decode("latin-1") for k, v in scope["headers"]}
        claimed = headers.get("origin")
        if claimed is None and "referer" in headers:
            claimed = headers["referer"]
        if claimed is not None:
            origin = None if claimed == "null" else _origin_of(claimed)
            if origin is None or not self._allowed(scope, origin):
                response = JSONResponse({"detail": "Cross-site request refused"}, status_code=403)
                await response(scope, receive, send)
                return
        await self.app(scope, receive, send)
