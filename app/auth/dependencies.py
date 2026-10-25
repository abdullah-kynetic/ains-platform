"""Authentication dependencies shared by API routers."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

import jwt
from fastapi import Cookie, Depends, Header, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.database.models import AuthSession, User
from app.database.session import get_db
from app.tenancy import assert_user_on_portal, require_firm_portal

from .security import decode_session_token

SESSION_COOKIE = "ains_session"
DB = Annotated[Session, Depends(get_db)]
AuthSettings = Annotated[Settings, Depends(get_settings)]
SessionCookie = Annotated[str | None, Cookie(alias=SESSION_COOKIE)]
AuthorizationHeader = Annotated[str | None, Header()]


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=UTC)


def session_cookie_flags(settings: Settings) -> dict[str, object]:
    """Host-only session cookie. ``Domain`` is omitted on purpose.

    A ``Domain=.kiensolutions.com`` cookie would be sent to every firm portal.
    ``SameSite=Lax`` does not separate sibling subdomains; the portal ``/api``
    proxy makes the cookie host-only for that firm's subdomain. See
    ``docs/multi-tenant-portals.md``.
    """
    return {
        "httponly": True,
        "secure": settings.session_cookie_secure,
        "samesite": "lax",
        "path": "/",
    }


def apply_session_cookie(response: Response, token: str, settings: Settings) -> None:
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=settings.session_ttl_hours * 3600,
        **session_cookie_flags(settings),
    )


def clear_session_cookie(response: Response, settings: Settings) -> None:
    response.delete_cookie(SESSION_COOKIE, **session_cookie_flags(settings))


def get_authenticated_session(
    db: DB,
    settings: AuthSettings,
    session_cookie: SessionCookie = None,
    authorization: AuthorizationHeader = None,
) -> tuple[AuthSession, User]:
    """Authenticate the presented session without resolving a portal firm."""
    token = session_cookie
    if not token and authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sign-in required")
    try:
        payload = decode_session_token(token, settings)
        session_id, user_id = str(payload["sid"]), str(payload["sub"])
    except (jwt.PyJWTError, KeyError, RuntimeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Session is invalid or expired"
        ) from None

    row = db.execute(
        select(AuthSession, User)
        .join(User, User.id == AuthSession.user_id)
        .where(
            AuthSession.id == session_id,
            AuthSession.user_id == user_id,
            AuthSession.revoked_at.is_(None),
            User.is_active.is_(True),
        )
    ).one_or_none()
    if not row or _aware(row.AuthSession.expires_at) <= datetime.now(UTC):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Session is invalid or expired"
        )
    return row.AuthSession, row.User


AuthenticatedSession = Annotated[tuple[AuthSession, User], Depends(get_authenticated_session)]


def get_current_user(
    request: Request, db: DB, settings: AuthSettings, authenticated: AuthenticatedSession
) -> User:
    _, user = authenticated
    assert_user_on_portal(user, require_firm_portal(request, settings, db))
    return user
