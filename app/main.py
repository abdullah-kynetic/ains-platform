"""FastAPI application factory and entrypoint."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import router as engagement_router
from app.auth import router as auth_router
from app.auth.invitations import auditor_router as invitation_auditor_router
from app.auth.invitations import public_router as invitation_public_router
from app.config import get_settings
from app.monitoring import init_sentry


def create_app() -> FastAPI:
    settings = get_settings()
    init_sentry(settings)
    application = FastAPI(title="AINS Platform", version="0.1.0")
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.parsed_cors_origins(),
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )
    from app.auth.reset import router as reset_router

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
