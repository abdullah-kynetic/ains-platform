"""FastAPI application factory and entrypoint."""

from fastapi import FastAPI

from app.api import router as engagement_router
from app.auth import router as auth_router
from app.auth.invitations import auditor_router as invitation_auditor_router
from app.auth.invitations import public_router as invitation_public_router
from app.config import get_settings
from app.cors import PortalCORSMiddleware, portal_origin_allowed
from app.monitoring import configure_private_logging, init_sentry
from app.origin_check import OriginCheckMiddleware
from app.ratelimit import RateLimitMiddleware
from app.security_headers import SecurityHeadersMiddleware


def enforce_production_safety(settings) -> None:
    """Refuse to start in production with unscanned uploads (no silent unsafe default)."""
    if settings.env != "production":
        return
    if settings.upload_scan_mode == "off":
        raise RuntimeError("ENV=production requires UPLOAD_SCAN_MODE=clamav; refusing to start")
    if not settings.session_cookie_secure:
        raise RuntimeError("ENV=production requires SESSION_COOKIE_SECURE=true; refusing to start")
    # The same allowlist is the CORS list and the exact-origin check for state-changing requests.
    # With PORTAL_BASE_DOMAIN set, firm hosts come from the database instead, so CORS_ORIGINS
    # may be empty; any entry that is listed must still be https with no wildcard or localhost.
    origins = settings.parsed_cors_origins()
    bad = [o for o in origins if not o.startswith("https://") or "*" in o or "localhost" in o]
    if (not origins and not settings.portal_base_domain) or bad:
        raise RuntimeError(
            "ENV=production requires PORTAL_BASE_DOMAIN or a CORS_ORIGINS list of https portal "
            "origins (no wildcard, no localhost); refusing to start"
        )


def create_app() -> FastAPI:
    settings = get_settings()
    enforce_production_safety(settings)
    configure_private_logging()
    init_sentry(settings)
    application = FastAPI(title="Kien Solutions", version="0.1.0")
    # Added before CORS so CORS stays outermost and 429 responses carry CORS headers.
    application.add_middleware(
        RateLimitMiddleware,
        per_minute=settings.api_rate_limit_per_minute,
        max_concurrent_uploads=settings.upload_max_concurrent,
    )
    application.add_middleware(
        OriginCheckMiddleware,
        allowed_origins=settings.parsed_cors_origins(),
        extra_allowed=portal_origin_allowed,
    )
    # Outermost. Exact CORS_ORIGINS entries plus, when PORTAL_BASE_DOMAIN is set, the apex, www,
    # auditor and https://<known firm slug>.<domain>. No wildcard is ever sent.
    application.add_middleware(PortalCORSMiddleware)
    # Outermost of all, so every response (errors, 429, CORS preflight) carries the headers.
    application.add_middleware(SecurityHeadersMiddleware)
    from app.auth.onboarding import router as onboarding_router
    from app.auth.reset import router as reset_router

    application.include_router(onboarding_router)
    application.include_router(reset_router)
    application.include_router(auth_router)
    application.include_router(invitation_public_router)
    application.include_router(invitation_auditor_router)
    application.include_router(engagement_router)

    @application.get("/health")
    def health() -> dict[str, str]:
        """Liveness check; deliberately does not expose configuration details."""
        return {"status": "ok"}

    return application


app = create_app()
