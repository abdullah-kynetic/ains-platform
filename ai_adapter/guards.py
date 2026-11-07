"""Guard rails: allowlist, price check, kill switch and breaker, SAR block, rate limit."""

import json
import threading
import time
from collections import deque
from collections.abc import Callable
from pathlib import Path

import httpx
import yaml

from ai_adapter.settings import AdapterSettings


class GuardViolation(Exception):
    """A guard refused the call. The message is safe to log (no document content)."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


FORBIDDEN_MODEL_MARKERS = (":online", "openrouter/")
ALLOWED_SOURCES = {"synthetic"}


def load_allowlist(path: Path) -> set[str]:
    models = json.loads(path.read_text())["models"]
    ids = {m["id"] if isinstance(m, dict) else m for m in models}
    for model_id in ids:
        if not model_id.endswith(":free") or any(
            marker in model_id for marker in FORBIDDEN_MODEL_MARKERS
        ):
            raise ValueError(f"allowlist entry is not an exact free model id: {model_id}")
    return ids


def restricted_item_ids(path: Path) -> set[str]:
    """SAR-related items come from the canonical checklist, never a hard-coded list."""
    data = yaml.safe_load(path.read_text())
    return {r["id"] for r in data["requests"] if r.get("restricted")}


class Breaker:
    """Opens on a guard violation or repeated errors; stays open until a person closes it."""

    def __init__(self, path: Path, max_errors: int):
        self.path, self.max_errors, self._errors = path, max_errors, 0

    @property
    def is_open(self) -> bool:
        try:
            return bool(json.loads(self.path.read_text()).get("open"))
        except FileNotFoundError:
            return False
        except (ValueError, OSError):
            return True  # unreadable state fails closed

    def open(self, reason: str) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps({"open": True, "reason": reason}))

    def close(self) -> None:  # called by a person (CLI/runbook), never by the adapter
        self.path.unlink(missing_ok=True)
        self._errors = 0

    def record_error(self) -> None:
        self._errors += 1
        if self._errors >= self.max_errors:
            self.open("repeated_errors")

    def record_success(self) -> None:
        self._errors = 0


class RateLimiter:
    def __init__(self, per_minute: int, daily_cap: int, clock: Callable[[], float] = time.time):
        self.per_minute, self.daily_cap, self.clock = per_minute, daily_cap, clock
        self._recent: deque[float] = deque()
        self._day = (clock() // 86400, 0)
        self._lock = threading.Lock()

    def acquire(self) -> None:
        with self._lock:
            now = self.clock()
            while self._recent and now - self._recent[0] >= 60:
                self._recent.popleft()
            day, used = self._day
            if day != now // 86400:
                day, used = now // 86400, 0
            if used >= self.daily_cap:
                raise GuardViolation("daily_quota_reached")
            if len(self._recent) >= self.per_minute:
                raise GuardViolation("rate_limited")
            self._recent.append(now)
            self._day = (day, used + 1)


class PriceChecker:
    """Refuses unless prompt, completion, request and image prices are exactly 0. Fails closed."""

    FIELDS = ("prompt", "completion", "request", "image")

    def __init__(self, settings: AdapterSettings, http: httpx.Client, clock=time.time):
        self.settings, self.http, self.clock = settings, http, clock
        self._cache: tuple[float, dict] | None = None

    def _models(self) -> dict:
        now = self.clock()
        if self._cache and now - self._cache[0] < self.settings.ai_price_cache_seconds:
            return self._cache[1]
        try:
            resp = self.http.get(f"{self.settings.openrouter_base_url}/models")
            resp.raise_for_status()
            data = {m["id"]: m for m in resp.json()["data"]}
        except Exception as exc:  # noqa: BLE001 - any failure refuses the call
            raise GuardViolation("price_list_unavailable") from exc
        self._cache = (now, data)
        return data

    def require_free(self, model_id: str) -> None:
        model = self._models().get(model_id)
        if model is None:
            raise GuardViolation("model_not_listed")
        pricing = model.get("pricing") or {}
        for field in self.FIELDS:
            # Missing means unknown, which is not free. Only the exact zero string passes.
            if str(pricing.get(field, "missing")).strip() not in {"0", "0.0", "0.00"}:
                raise GuardViolation("model_not_free")
