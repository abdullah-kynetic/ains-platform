"""Invite-only password and magic-link sign-in endpoints.

Magic-link delivery is intentionally an injectable boundary. The default sender records no
token and emits no logs; deployment must supply an email delivery adapter before enabling that
method. Tests inject a capture sender without exposing real credentials.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Annotated, Protocol

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.database.models import AuditLog, AuthSession, MagicLinkToken, User, UserRole
from app.database.session import get_db

from .dependencies import SESSION_COOKIE, get_current_user
from .security import (
    create_session_token,
    hash_magic_link_token,
    new_magic_link_token,
    verify_password,
    verify_totp,
)

router = APIRouter(prefix="/auth", tags=["auth"])
DB = Annotated[Session, Depends(get_db)]
AuthSettings = Annotated[Settings, Depends(get_settings)]


class PasswordSignIn(BaseModel):
    email: str
    password: str = Field(min_length=8, max_length=1024)
    mfa_code: str | None = Field(default=None, min_length=6, max_length=8)


class MagicLinkRequest(BaseModel):
    email: str


class MagicLinkVerify(BaseModel):
    token: str = Field(min_length=20, max_length=512)
    mfa_code: str | None = Field(default=None, min_length=6, max_length=8)


class UserView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    name: str
    role: UserRole
    firm_id: str | None


class SessionView(BaseModel):
    user: UserView


class MagicLinkSender(Protocol):
    def send(self, *, email: str, token: str, expires_at: datetime) -> None: ...


class UnconfiguredMagicLinkSender:
    def send(self, *, email: str, token: str, expires_at: datetime) -> None:
        # Never log or return a sign-in token. A production email adapter replaces this dependency.
        del email, token, expires_at


def get_magic_link_sender() -> MagicLinkSender:
    return UnconfiguredMagicLinkSender()


MagicSender = Annotated[MagicLinkSender, Depends(get_magic_link_sender)]
CurrentUser = Annotated[User, Depends(get_current_user)]


def _normalize_email(email: str) -> str:
    return email.strip().casefold()


def _require_auditor_mfa(user: User, code: str | None) -> None:
    if user.role != UserRole.AUDITOR:
        return
    if not user.mfa_enabled or not user.mfa_secret:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Auditor MFA enrollment is required",
        )
    if not code:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="MFA code required")
    if not verify_totp(user.mfa_secret, code):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid MFA code")


def _issue_session(
    *, db: Session, settings: Settings, response: Response, user: User
) -> SessionView:
    now = datetime.now(UTC)
    auth_session = AuthSession(
        user_id=user.id, expires_at=now + timedelta(hours=settings.session_ttl_hours)
    )
    db.add(auth_session)
    db.flush()
    try:
        token = create_session_token(
            user_id=user.id, session_id=auth_session.id, settings=settings, now=now
        )
    except RuntimeError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication is not configured",
        ) from None
    db.add(
        AuditLog(
            firm_id=user.firm_id,
            actor_id=user.id,
            action="auth.session_created",
            entity_type="user",
            entity_id=user.id,
        )
    )
    db.commit()
    response.set_cookie(
        SESSION_COOKIE,
        token,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
        max_age=settings.session_ttl_hours * 3600,
        path="/",
    )
    return SessionView(user=UserView.model_validate(user))


@router.post("/password", response_model=SessionView)
def password_sign_in(
    payload: PasswordSignIn,
    response: Response,
    db: DB,
    settings: AuthSettings,
) -> SessionView:
    user = db.scalar(select(User).where(User.email == _normalize_email(payload.email)))
    if not user or not user.is_active or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password"
        )
    _require_auditor_mfa(user, payload.mfa_code)
    return _issue_session(db=db, settings=settings, response=response, user=user)


@router.post("/magic-link", status_code=status.HTTP_202_ACCEPTED)
def request_magic_link(
    payload: MagicLinkRequest,
    db: DB,
    settings: AuthSettings,
    sender: MagicSender,
) -> dict[str, str]:
    user = db.scalar(select(User).where(User.email == _normalize_email(payload.email)))
    if user and user.is_active:
        token, token_hash = new_magic_link_token()
        expires = datetime.now(UTC) + timedelta(minutes=settings.magic_link_ttl_minutes)
        db.add(MagicLinkToken(user_id=user.id, token_hash=token_hash, expires_at=expires))
        db.commit()
        sender.send(email=user.email, token=token, expires_at=expires)
    return {"status": "accepted"}


@router.post("/magic-link/verify", response_model=SessionView)
def verify_magic_link(
    payload: MagicLinkVerify,
    response: Response,
    db: DB,
    settings: AuthSettings,
) -> SessionView:
    record = db.scalar(
        select(MagicLinkToken).where(
            MagicLinkToken.token_hash == hash_magic_link_token(payload.token),
            MagicLinkToken.used_at.is_(None),
        )
    )
    now = datetime.now(UTC)
    if (
        not record
        or (
            record.expires_at.replace(tzinfo=UTC)
            if not record.expires_at.tzinfo
            else record.expires_at
        )
        <= now
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Magic link is invalid or expired"
        )
    user = db.get(User, record.user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Magic link is invalid or expired"
        )
    _require_auditor_mfa(user, payload.mfa_code)
    record.used_at = now
    return _issue_session(db=db, settings=settings, response=response, user=user)


@router.get("/session", response_model=SessionView)
def read_session(user: CurrentUser) -> SessionView:
    return SessionView(user=UserView.model_validate(user))


@router.post("/sign-out", status_code=status.HTTP_204_NO_CONTENT)
def sign_out(
    response: Response,
    user: CurrentUser,
    db: DB,
) -> None:
    # Revoking all current sessions is conservative and appropriate for the first release.
    for auth_session in db.scalars(
        select(AuthSession).where(AuthSession.user_id == user.id, AuthSession.revoked_at.is_(None))
    ):
        auth_session.revoked_at = datetime.now(UTC)
    db.commit()
    response.delete_cookie(SESSION_COOKIE, path="/")
