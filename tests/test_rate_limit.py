"""Request-rate and concurrent-upload limits (pure ASGI, synthetic traffic only)."""

import asyncio

import httpx
import pytest

from app.config import Settings
from app.ratelimit import RateLimitMiddleware


async def _ok(scope, receive, send):
    await send({"type": "http.response.start", "status": 200, "headers": []})
    await send({"type": "http.response.body", "body": b"ok"})


def _client(app, ip="198.51.100.1"):
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app, client=(ip, 5000)), base_url="http://t"
    )


async def test_rate_limit_per_client_with_retry_after_and_health_exempt():
    now = [0.0]
    app = RateLimitMiddleware(_ok, per_minute=3, max_concurrent_uploads=0, clock=lambda: now[0])
    async with _client(app) as a, _client(app, "198.51.100.2") as b:
        assert [(await a.get("/x")).status_code for _ in range(3)] == [200, 200, 200]
        blocked = await a.get("/x")
        assert blocked.status_code == 429 and blocked.headers["Retry-After"] == "60"
        assert (await a.get("/health")).status_code == 200  # uptime checks never throttled
        assert (await b.get("/x")).status_code == 200  # other addresses are unaffected
        now[0] += 61
        assert (await a.get("/x")).status_code == 200


async def test_zero_disables_limits():
    app = RateLimitMiddleware(_ok, per_minute=0, max_concurrent_uploads=0)
    async with _client(app) as c:
        assert all([(await c.get("/x")).status_code == 200 for _ in range(50)])


async def test_concurrent_uploads_are_capped_and_released():
    gate = asyncio.Event()
    started = 0

    async def slow(scope, receive, send):
        nonlocal started
        if scope["method"] == "POST":
            started += 1
            await gate.wait()
        await _ok(scope, receive, send)

    app = RateLimitMiddleware(slow, per_minute=0, max_concurrent_uploads=2)
    path = "/engagements/e1/items/i1/documents"
    async with _client(app) as c:
        first = [asyncio.create_task(c.post(path, content=b"x")) for _ in range(2)]
        while started < 2:
            await asyncio.sleep(0)
        refused = await c.post("/engagements/e1/documents", content=b"x")
        assert refused.status_code == 429 and "Retry-After" in refused.headers
        assert (await c.get(path)).status_code == 200  # only POST uploads are counted
        gate.set()
        assert [r.status_code for r in await asyncio.gather(*first)] == [200, 200]
        assert (await c.post(path, content=b"x")).status_code == 200  # slots were released


async def test_upload_slot_released_when_the_handler_fails():
    async def boom(scope, receive, send):
        raise RuntimeError("synthetic failure")

    app = RateLimitMiddleware(boom, per_minute=0, max_concurrent_uploads=1)
    async with _client(app) as c:
        for _ in range(2):
            with pytest.raises(RuntimeError):
                await c.post("/engagements/e1/documents", content=b"x")
    assert app._uploads_in_flight == 0


def test_defaults_are_enabled():
    settings = Settings(_env_file=None)
    assert settings.api_rate_limit_per_minute == 300
    assert settings.upload_max_concurrent == 3
