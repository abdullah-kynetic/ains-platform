"""Client-side rate limiter.

Egnyte's default limits are 2 calls/second and 1,000 calls/day per access token:
https://developers.egnyte.com/docs/read/Best_Practices (Rate Limiting)
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable


class RateLimiter:
    """Spaces calls at least ``1 / max_per_second`` seconds apart."""

    def __init__(
        self,
        max_per_second: float = 2.0,
        *,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self.min_interval = 1.0 / max_per_second if max_per_second > 0 else 0.0
        self._clock = clock
        self._sleep = sleep
        self._next_allowed = 0.0
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            now = self._clock()
            wait = self._next_allowed - now
            if wait > 0:
                await self._sleep(wait)
                now = self._next_allowed
            self._next_allowed = now + self.min_interval
