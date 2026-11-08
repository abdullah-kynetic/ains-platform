"""FastAPI application factory and entrypoint."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import router as engagement_router
from app.auth import router as auth_router
from app.auth.invitations import auditor_router as invitation_auditor_router
from app.auth.invitations import public_router as invitation_public_router
from app.config import get_settings
from app.monitoring import init_sentry
from app.origin_check import OriginCheckMiddleware
from app.ratelimit import RateLimitMiddleware


def enforce_production_safety(settings) -> None:
    """Refuse to start in production with unscanned uploads (no silent unsafe default)."""
    if settings.env != "production":
        return
    if settings.upload_scan_mode == "off":
        raise RuntimeError("ENV=production requires UPLOAD_SCAN_MODE=clamav; refusing to start")
    if not settings.session_cookie_secure:
        raise RuntimeError("ENV=production requires SESSION_COOKIE_SECURE=true; refusing to start")
    # The same list is the CORS list and the exact-origin allowlist for state-changing requests,
    # so every portal host (each firm host and the auditor host) must be listed, as https.
    origins = settings.parsed_cors_origins()
    bad = [o for o in origins if not o.startswith("https://") or "*" in o or "localhost" in o]
    if not origins or bad:
        raise RuntimeError(
            "ENV=production requires CORS_ORIGINS to list every portal origin as https "
            "(no wildcard, no localhost); refusing to start"
        )


def create_app() -> FastAPI:
    settings = get_settings()
    enforce_production_safety(settings)
    init_sentry(settings)
    application = FastAPI(title="Kien Solutions", version="0.1.0")
    # Added before CORS so CORS stays outermost and 429 responses carry CORS headers.
    application.add_middleware(
        RateLimitMiddleware,
        per_minute=settings.api_rate_limit_per_minute,
        max_concurrent_uploads=settings.upload_max_concurrent,
    )
    application.add_middleware(
        OriginCheckMiddleware, allowed_origins=settings.parsed_cors_origins()
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.parsed_cors_origins(),
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
        # The web app reads Retry-After to tell a locked-out user how long to wait.
        expose_headers=["Retry-After"],
    )
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
