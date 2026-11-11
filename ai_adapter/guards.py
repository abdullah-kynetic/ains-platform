"""Guard rails: allowlist, price check, kill switch and breaker, SAR block, rate limit."""

import json
import re
import threading
import time
import unicodedata
from collections import deque
from collections.abc import Callable
from decimal import Decimal, InvalidOperation
from pathlib import Path

import httpx
import yaml

from ai_adapter.settings import AdapterSettings
from ai_adapter.state import StateStore


class GuardViolation(Exception):
    """A guard refused the call. The message is safe to log (no document content)."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


# Content scan: SAR / suspicious activity report filings must never reach a model. Fails closed
# on any mention. Text is folded first (NFKD, invisible characters dropped, look-alike Cyrillic and
# Greek letters mapped to Latin, case folded) and then reduced to letters separated by single
# spaces, so "SAR_Q3_2026", "SAR2026", "S.A.R." and "S A R" all read as the word SAR. Ordinary AML
# policy text that merely names SAR procedures is blocked too: a person reviews those, not a model.
_CONFUSABLES = str.maketrans(
    {
        # Cyrillic
        "а": "a", "е": "e", "о": "o", "р": "p", "с": "c", "х": "x", "у": "y", "і": "i",
        "ј": "j", "ѕ": "s", "к": "k", "м": "m", "н": "h", "т": "t", "в": "b", "г": "r",
        "ԁ": "d", "ӏ": "l", "ѵ": "v", "ԛ": "q", "ԝ": "w", "ь": "b", "ё": "e", "ї": "i",
        # Greek
        "α": "a", "ε": "e", "ο": "o", "ρ": "p", "τ": "t", "υ": "u", "ν": "v", "ι": "i",
        "κ": "k", "ς": "s", "σ": "s", "η": "n", "μ": "u", "β": "b", "χ": "x", "γ": "y",
        # Other Latin look-alikes
        "ı": "i", "ɑ": "a", "ɡ": "g", "ʀ": "r",
    }
)  # fmt: skip
_INVISIBLE = dict.fromkeys(
    [0x200B, 0x200C, 0x200D, 0x2060, 0xFEFF, 0x00AD, 0x180E, 0x034F]
    + list(range(0x202A, 0x202F))
    + list(range(0x2066, 0x206A)),
    None,
)
_SAR_PATTERNS = (
    re.compile(r"\bs ?a ?r(?: ?s)?\b"),  # SAR, SARs, S A R, SAR_Q3 (non-letters became spaces)
    re.compile(r"\bsar(?:narrative|filing|report|decision|referral|log)"),  # SARnarrative
    re.compile(r"\bsuspicious activit(?:y|ies) (?:report|rpt|filing|narrative|form)"),
    re.compile(r"\b(?:report|reports|rpt|rpts|reporting|filing|filings|filed|file) "
               r"(?:of|on|for|about) suspicious (?:activit|transaction)"),
    re.compile(r"\bsuspicious (?:activit(?:y|ies)|transactions?) (?:rpts?|reps?)\b"),
    re.compile(r"\bsuspicious transaction report"),
    re.compile(r"\bfincen (?:form )?sar"),
    re.compile(r"\bbsa e ?filing"),
)  # fmt: skip


_FORM_111 = re.compile(r"fincen[^a-z0-9]*(?:form[^a-z0-9]*)?111(?!\d)")


def _fold(raw: str, keep_digits: bool = False) -> str:
    text = unicodedata.normalize("NFKD", raw).translate(_INVISIBLE).casefold()
    text = "".join(ch for ch in text if not unicodedata.combining(ch)).translate(_CONFUSABLES)
    return " ".join(re.sub(r"[^a-z0-9]+" if keep_digits else r"[^a-z]+", " ", text).split())


def sar_content_reason(*texts: str) -> str | None:
    """Return a short reason code when any text mentions SAR material, else None."""
    for raw in texts:
        folded = _fold(raw)
        if any(pattern.search(folded) for pattern in _SAR_PATTERNS) or _FORM_111.search(
            _fold(raw, keep_digits=True)
        ):
            return "sar_content"
    return None


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

    def __init__(self, path: Path, max_errors: int, store: StateStore):
        self.path, self.max_errors, self.store = path, max_errors, store

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
        self.store.clear_errors()

    def record_error(self) -> None:
        if self.store.add_error() >= self.max_errors:
            self.open("repeated_errors")

    def record_success(self) -> None:
        self.store.clear_errors()


class RateLimiter:
    """Per-minute window in memory; the daily cap is persisted so a restart cannot reset it."""

    def __init__(
        self,
        per_minute: int,
        daily_cap: int,
        store: StateStore,
        clock: Callable[[], float] = time.time,
    ):
        self.per_minute, self.daily_cap, self.store, self.clock = (
            per_minute,
            daily_cap,
            store,
            clock,
        )
        self._recent: deque[float] = deque()
        self._lock = threading.Lock()

    def acquire(self) -> None:
        with self._lock:
            now = self.clock()
            while self._recent and now - self._recent[0] >= 60:
                self._recent.popleft()
            if len(self._recent) >= self.per_minute:
                raise GuardViolation("rate_limited")
            if not self.store.take_daily(self.daily_cap):
                raise GuardViolation("daily_quota_reached")
            self._recent.append(now)


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
        # Missing means unknown, which is not free. EVERY listed price must parse to exactly zero
        # (including cache, web-search or reasoning prices), and the four basic fields must exist.
        if not set(self.FIELDS) <= pricing.keys():
            raise GuardViolation("model_not_free")
        for value in pricing.values():
            try:
                if Decimal(str(value).strip()) != 0:
                    raise GuardViolation("model_not_free")
            except InvalidOperation:
                raise GuardViolation("model_not_free") from None
