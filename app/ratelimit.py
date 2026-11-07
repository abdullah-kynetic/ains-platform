"""In-process API protection: per-client request rate and concurrent document uploads.

Counters live in this process, which is correct for the single-worker production container.
Behind Caddy the client address is the forwarded one (uvicorn --proxy-headers, trusted proxy only).
The password-reset and sign-in throttles in the database remain the account-level controls.
"""

import re
import time
from collections import deque
from collections.abc import Callable

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

UPLOAD_PATH = re.compile(r"^/engagements/[^/]+/(items/[^/]+/)?documents$")
EXEMPT_PATHS = {"/health"}
MAX_TRACKED_CLIENTS = 10_000


class RateLimitMiddleware:
    def __init__(
        self,
        app: ASGIApp,
        *,
        per_minute: int,
        max_concurrent_uploads: int,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.app = app
        self.per_minute = per_minute  # 0 disables the request-rate limit
        self.max_uploads = max_concurrent_uploads  # 0 disables the upload limit
        self.clock = clock
        self._hits: dict[str, deque[float]] = {}
        self._uploads_in_flight = 0

    def _over_rate(self, client: str) -> bool:
        now = self.clock()
        if len(self._hits) > MAX_TRACKED_CLIENTS:
            self._hits = {k: v for k, v in self._hits.items() if v and now - v[-1] < 60}
        hits = self._hits.setdefault(client, deque())
        while hits and now - hits[0] >= 60:
            hits.popleft()
        if len(hits) >= self.per_minute:
            return True
        hits.append(now)
        return False

    @staticmethod
    async def _reject(scope: Scope, receive: Receive, send: Send, detail: str, wait: int) -> None:
        response = JSONResponse(
            {"detail": detail}, status_code=429, headers={"Retry-After": str(wait)}
        )
        await response(scope, receive, send)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["path"] in EXEMPT_PATHS or scope["method"] == "OPTIONS":
            await self.app(scope, receive, send)
            return
        client = scope["client"][0] if scope.get("client") else "unknown"
        if self.per_minute and self._over_rate(client):
            await self._reject(scope, receive, send, "Too many requests", 60)
            return
        is_upload = scope["method"] == "POST" and UPLOAD_PATH.match(scope["path"])
        if is_upload and self.max_uploads:
            if self._uploads_in_flight >= self.max_uploads:
                await self._reject(scope, receive, send, "Too many uploads in progress", 5)
                return
            self._uploads_in_flight += 1
            try:
                await self.app(scope, receive, send)
            finally:
                self._uploads_in_flight -= 1
            return
        await self.app(scope, receive, send)
