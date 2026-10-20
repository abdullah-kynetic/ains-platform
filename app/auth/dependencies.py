"""Authentication dependencies shared by API routers."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

import jwt
from fastapi import Cookie, Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.database.models import AuthSession, User
from app.database.session import get_db

from .security import decode_session_token

SESSION_COOKIE = "ains_session"
DB = Annotated[Session, Depends(get_db)]
AuthSettings = Annotated[Settings, Depends(get_settings)]
SessionCookie = Annotated[str | None, Cookie(alias=SESSION_COOKIE)]
AuthorizationHeader = Annotated[str | None, Header()]


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=UTC)


def get_current_user(
    db: DB,
    settings: AuthSettings,
    session_cookie: SessionCookie = None,
    authorization: AuthorizationHeader = None,
) -> User:
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
    return row.User
