"""Firm portal hosts.

Each licensed firm is served at ``https://<slug>.<portal base>``. The slug is a
lowercase DNS label stored on ``firms.slug``. Reserved labels are infrastructure
hosts and can never be assigned to a firm.

Session checks compare that label with the browser Origin and, when those headers
agree, the forwarded host. See ``docs/multi-tenant-portals.md``.
"""

from __future__ import annotations

import re
import threading
import time
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Literal
from urllib.parse import urlsplit

from fastapi import HTTPException, Request
from sqlalchemy import event, select
from sqlalchemy.orm import Session

from app.config import Settings
from app.database.models import Firm, User, UserRole

# Hosts that must keep serving the landing page or shared infrastructure.
# "auditor" is the fixed auditor host; the rest match NON_FIRM_LABELS in web/src/lib/audience.ts.
AUDITOR_LABEL = "auditor"
RESERVED_SLUGS = frozenset(
    {"www", "api", "app", "admin", "mail", "status", "preview", "design", "layout", AUDITOR_LABEL}
)
SLUG_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")
PortalKind = Literal[
    "disabled", "firm", "auditor", "landing", "reserved", "absent", "invalid", "conflict"
]


class AuditorHost:
    """The fixed auditor host (``auditor.<base>``). Only auditor sessions may use it."""

    def __repr__(self) -> str:
        return "AUDITOR_HOST"


AUDITOR_HOST = AuditorHost()


def dev_localhost_portals_enabled(settings: Settings) -> bool:
    """``http://<slug>.localhost:<port>`` is a firm portal only for local development.

    Production sets ``PORTAL_BASE_DOMAIN`` and ``SESSION_COOKIE_SECURE``. Either one
    turns this off, so a production config cannot accept localhost firm origins.
    """
    return not settings.portal_base_domain and not settings.session_cookie_secure


def require_logo_url(value: str | None) -> str | None:
    """Public logo only: a site path or an https URL. Empty becomes unset."""
    if value is None:
        return None
    if not isinstance(value, str) or value != value.strip() or any(c in value for c in "\r\n\\ "):
        raise ValueError("logo url must be a relative path or https URL")
    if not value or ".." in value or len(value) > 500:
        raise ValueError("logo url must be a relative path or https URL")
    if value.startswith("/") or value.startswith("https://"):
        return value
    raise ValueError("logo url must be a relative path or https URL")


def require_firm_slug(value: str) -> str:
    """Return a canonical portal label or raise ValueError."""
    if not isinstance(value, str) or value != value.strip() or value != value.lower():
        raise ValueError("firm slug must be a lowercase DNS label")
    if value in RESERVED_SLUGS or SLUG_RE.fullmatch(value) is None:
        raise ValueError("firm slug must be a lowercase DNS label that is not reserved")
    return value


def allocate_firm_slug(db: Session, name: str) -> str:
    """Pick a unique portal label from a display name, skipping reserved hosts."""
    base = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    base = base[:63].strip("-") or "client"
    suffix = 1
    while suffix <= 1000:
        if suffix == 1:
            slug = base
        else:
            extra = f"-{suffix}"
            trimmed = base[: 63 - len(extra)].strip("-") or "client"
            slug = f"{trimmed}{extra}"
        suffix += 1
        if slug in RESERVED_SLUGS or SLUG_RE.fullmatch(slug) is None:
            continue
        if db.scalar(select(Firm.id).where(Firm.slug == slug)) is None:
            return slug
    raise RuntimeError("no firm slug available")


def portal_url_for(settings: Settings, slug: str | None) -> str:
    """Expand ``PORTAL_URL``. A concrete URL is returned unchanged.

    ``https://{slug}.kiensolutions.com`` becomes that firm's origin. With no firm
    (a platform auditor), the ``{slug}.`` label is removed so the link stays on
    the apex. The slug is validated before substitution.
    """
    template = settings.portal_url.strip()
    if "{slug}" not in template:
        return template.rstrip("/")
    if slug is None:
        marker = "://{slug}."
        if marker not in template:
            raise ValueError("PORTAL_URL requires a firm slug")
        return template.replace(marker, "://", 1).rstrip("/")
    return template.replace("{slug}", require_firm_slug(slug), 1).rstrip("/")


@dataclass(frozen=True)
class PortalDecision:
    enforced: bool
    kind: PortalKind
    slug: str | None = None


def _hostname_from_host_header(value: str) -> str | None:
    raw = value.split(",")[0].strip().lower().rstrip(".")
    if not raw or any(char in raw for char in " /@\\"):
        return None
    if raw.startswith("["):
        return None
    if ":" in raw:
        host, port = raw.rsplit(":", 1)
        if not port.isdigit() or not host:
            return None
        return host
    return raw


def host_kind(hostname: str, base: str) -> tuple[str, str | None]:
    host = hostname.lower().rstrip(".")
    if host == base:
        return "landing", None
    suffix = f".{base}"
    if not host.endswith(suffix) or host == suffix:
        return "unrelated", None
    label = host[: -len(suffix)]
    if label == "www":
        return "landing", "www"
    if label == AUDITOR_LABEL:
        return "auditor", AUDITOR_LABEL
    if label in RESERVED_SLUGS:
        if SLUG_RE.fullmatch(label) is None:
            return "invalid", None
        return "reserved", label
    if SLUG_RE.fullmatch(label) is None:
        return "invalid", None
    return "firm", label


def _is_localhost_name(hostname: str) -> bool:
    host = hostname.lower().rstrip(".")
    return host == "localhost" or host.endswith(".localhost")


def localhost_portal_kind(hostname: str) -> tuple[str, str | None]:
    """Classify ``localhost`` or ``<label>.localhost``. The port is not part of the label."""
    host = hostname.lower().rstrip(".")
    if host == "localhost":
        return "unrelated", None
    if not host.endswith(".localhost"):
        return "unrelated", None
    label = host[: -len(".localhost")]
    if not label or "." in label or SLUG_RE.fullmatch(label) is None:
        return "invalid", None
    if label in RESERVED_SLUGS:
        return "reserved", label
    return "firm", label


def _hostname_signal(hostname: str, settings: Settings) -> tuple[str, str | None]:
    if _is_localhost_name(hostname):
        if not dev_localhost_portals_enabled(settings):
            return "unrelated", None
        return localhost_portal_kind(hostname)
    if settings.portal_base_domain:
        return host_kind(hostname, settings.portal_base_domain)
    return "unrelated", None


def _origin_signal(origin: str, settings: Settings) -> tuple[str, str | None]:
    parsed = urlsplit(origin.strip())
    if (
        parsed.scheme not in {"http", "https"}
        or parsed.hostname is None
        or parsed.username
        or parsed.password
        or parsed.path not in {"", "/"}
        or parsed.query
        or parsed.fragment
    ):
        return "invalid", None
    if _is_localhost_name(parsed.hostname) and parsed.scheme != "http":
        return "unrelated", None
    return _hostname_signal(parsed.hostname, settings)


def resolve_portal(request: Request, settings: Settings) -> PortalDecision:
    """Map Origin, X-Forwarded-Host and Host onto one portal decision.

    With no production base domain and secure cookies off, ``http://<slug>.localhost``
    is a firm portal (the dev server uses port 3000). That match is ignored when
    ``PORTAL_BASE_DOMAIN`` or ``SESSION_COOKIE_SECURE`` is set. A bare ``localhost``
    or ``testserver`` host does not turn enforcement on. ``api.<base>`` is ignored
    when a firm origin is also present. Two different firm labels conflict.
    """
    base = settings.portal_base_domain
    dev_localhost = dev_localhost_portals_enabled(settings)
    if not base and not dev_localhost:
        return PortalDecision(enforced=False, kind="disabled")

    signals: list[tuple[str, str | None]] = []
    origin = request.headers.get("origin")
    if origin and origin.strip().lower() != "null":
        signals.append(_origin_signal(origin, settings))
    for header in ("x-forwarded-host", "host"):
        raw = request.headers.get(header)
        if not raw:
            continue
        hostname = _hostname_from_host_header(raw)
        if hostname is None:
            signals.append(("invalid", None))
        else:
            signals.append(_hostname_signal(hostname, settings))

    if not base and dev_localhost and all(kind == "unrelated" for kind, _slug in signals):
        return PortalDecision(enforced=False, kind="disabled")

    relevant = [(kind, slug) for kind, slug in signals if kind != "unrelated"]
    if any(kind == "invalid" for kind, _slug in relevant):
        return PortalDecision(True, "invalid")
    firm_slugs = {slug for kind, slug in relevant if kind == "firm" and slug}
    if len(firm_slugs) > 1:
        return PortalDecision(True, "conflict")
    auditor = any(kind == "auditor" for kind, _slug in relevant)
    if auditor and firm_slugs:
        return PortalDecision(True, "conflict")
    if auditor:
        return PortalDecision(True, "auditor")
    if len(firm_slugs) == 1:
        mixed = any(
            kind == "landing" or (kind == "reserved" and slug != "api") for kind, slug in relevant
        )
        if mixed:
            return PortalDecision(True, "conflict")
        return PortalDecision(True, "firm", slug=next(iter(firm_slugs)))
    if any(kind == "landing" for kind, _slug in relevant):
        return PortalDecision(True, "landing")
    if any(kind == "reserved" for kind, _slug in relevant):
        return PortalDecision(True, "reserved")
    return PortalDecision(True, "absent")


def require_firm_portal(
    request: Request, settings: Settings, db: Session
) -> Firm | AuditorHost | None:
    """Return the firm (or the auditor host) for this request. None means enforcement is off."""
    decision = resolve_portal(request, settings)
    if not decision.enforced:
        return None
    if decision.kind == "auditor":
        return AUDITOR_HOST
    if decision.kind != "firm" or not decision.slug:
        raise HTTPException(status_code=403, detail="Firm portal host is required")
    firm = db.scalar(select(Firm).where(Firm.slug == decision.slug))
    if firm is None:
        raise HTTPException(status_code=404, detail="Unknown firm portal")
    return firm


def assert_user_on_portal(user: User, firm: Firm | AuditorHost | None) -> None:
    """Reject a session whose firm is not the portal firm.

    The auditor host accepts auditors only. A client session is refused there.

    Platform auditors have no ``firm_id``. They may open a resolved firm portal;
    engagement queries still limit them to assignments. Every firm-bound user,
    including a white-label auditor, must match the portal.
    """
    if firm is None:
        return
    if isinstance(firm, AuditorHost):
        if user.role != UserRole.AUDITOR:
            raise HTTPException(status_code=403, detail="Session firm does not match this portal")
        return
    if user.firm_id is None:
        if user.role == UserRole.AUDITOR:
            return
        raise HTTPException(status_code=403, detail="Session firm does not match this portal")
    if user.firm_id != firm.id:
        raise HTTPException(status_code=403, detail="Session firm does not match this portal")


class SlugCache:
    """Short-lived set of portal labels. CORS uses this instead of a subdomain regex."""

    def __init__(self, ttl_seconds: float = 30.0) -> None:
        self.ttl_seconds = ttl_seconds
        self._lock = threading.Lock()
        self._expires_at = 0.0
        self._slugs: frozenset[str] = frozenset()

    def get(self, loader: Callable[[], Iterable[str]]) -> frozenset[str]:
        now = time.monotonic()
        with self._lock:
            if now < self._expires_at:
                return self._slugs
        loaded = frozenset(loader())
        with self._lock:
            self._slugs = loaded
            self._expires_at = time.monotonic() + self.ttl_seconds
            return self._slugs

    def clear(self) -> None:
        with self._lock:
            self._expires_at = 0.0
            self._slugs = frozenset()


SLUG_CACHE = SlugCache()


def load_firm_slugs() -> set[str]:
    from app.database.session import get_session_factory

    with get_session_factory()() as session:
        return set(session.scalars(select(Firm.slug)).all())


def known_portal_slugs(state_slugs: Iterable[str] | None) -> frozenset[str]:
    if state_slugs is not None:
        return frozenset(state_slugs)
    try:
        return SLUG_CACHE.get(load_firm_slugs)
    except Exception:
        return frozenset()


@event.listens_for(Firm, "after_insert")
@event.listens_for(Firm, "after_update")
@event.listens_for(Firm, "after_delete")
def _invalidate_portal_slug_cache(_mapper, _connection, _target) -> None:
    SLUG_CACHE.clear()
