"""Invite-only password and magic-link sign-in with injectable Resend delivery."""

from __future__ import annotations

import hashlib
import logging
from datetime import UTC, datetime, timedelta
from typing import Annotated, Literal, Protocol

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.database.models import (
    AuditLog,
    AuthSession,
    Firm,
    MagicLinkToken,
    User,
    UserRole,
)
from app.database.session import get_db
from app.tenancy import assert_user_on_portal, require_firm_portal

from .dependencies import SESSION_COOKIE, AuthenticatedUser, get_current_user
from .email_code import (
    EMAIL_CODE_REQUIRED,
    CodeSender,
    device_cookie_name,
    get_code_sender,
    is_trusted_device,
    remember_device,
    revoke_devices,
    revoke_other_sessions,
    send_code,
    verify_code,
    warn_fallback,
)
from .lockout import SignInGuard
from .security import (
    create_session_token,
    decode_session_token,
    hash_magic_link_token,
    new_magic_link_token,
    verify_and_rehash_password,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])
DB = Annotated[Session, Depends(get_db)]
AuthSettings = Annotated[Settings, Depends(get_settings)]


class PasswordSignIn(BaseModel):
    email: str
    password: str = Field(min_length=8, max_length=1024)
    # The 6-digit code emailed after a correct password (only when email codes are active).
    code: str | None = Field(default=None, min_length=6, max_length=12)
    remember_device: bool = False


class EmailCodeResend(BaseModel):
    email: str
    password: str = Field(min_length=8, max_length=1024)


class MagicLinkRequest(BaseModel):
    email: str


class MagicLinkVerify(BaseModel):
    token: str = Field(min_length=20, max_length=512)


class UserView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    name: str
    role: UserRole
    firm_id: str | None
    onboarding_state: Literal["completed", "skipped"] | None


class SessionView(BaseModel):
    user: UserView


class MagicLinkSender(Protocol):
    def send(
        self, *, email: str, token: str, expires_at: datetime, slug: str | None = None
    ) -> None: ...


class UnconfiguredMagicLinkSender:
    def send(
        self, *, email: str, token: str, expires_at: datetime, slug: str | None = None
    ) -> None:
        # Never log or return a sign-in token. A production email adapter replaces this dependency.
        del email, token, expires_at, slug


def get_magic_link_sender(settings: AuthSettings) -> MagicLinkSender:
    from .email import ResendSender

    if settings.resend_api_key.get_secret_value() and settings.email_from:
        return ResendSender(settings)
    return UnconfiguredMagicLinkSender()


MagicSender = Annotated[MagicLinkSender, Depends(get_magic_link_sender)]
CurrentUser = Annotated[User, Depends(get_current_user)]


@router.get("/capabilities")
def auth_capabilities(settings: AuthSettings, sender: MagicSender) -> dict[str, bool]:
    configured = len(settings.session_secret.get_secret_value().encode()) >= 32
    return {
        "password_sign_in": configured,
        "magic_link": configured and not isinstance(sender, UnconfiguredMagicLinkSender),
        "email_code": configured and settings.email_codes_active,
    }


def _normalize_email(email: str) -> str:
    return email.strip().casefold()


def _password_user(db: Session, email: str, password: str) -> User:
    user = db.scalar(select(User).where(User.email == _normalize_email(email)))
    valid, upgraded = (
        verify_and_rehash_password(password, user.password_hash)
        if user and user.is_active
        else (False, None)
    )
    if not valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password"
        )
    if upgraded:
        user.password_hash = upgraded
    return user


def _authenticate(
    db: Session,
    request: Request,
    settings: Settings,
    email: str,
    password: str,
) -> User:
    """Password check behind the failed-attempt lockout."""
    guard = SignInGuard(db, request, settings, "signin", email)
    guard.check()
    portal = require_firm_portal(request, settings, db)
    try:
        user = _password_user(db, email, password)
    except HTTPException as exc:
        if exc.status_code == status.HTTP_401_UNAUTHORIZED:
            db.rollback()
            guard.fail()
        raise
    # A valid account may only sign in on its own firm portal. No session or cookie is issued.
    assert_user_on_portal(user, portal)
    guard.succeed()
    return user


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
            user_id=user.id,
            session_id=auth_session.id,
            settings=settings,
            now=now,
            role=user.role.value,
            firm_id=user.firm_id,
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
    request: Request,
    response: Response,
    db: DB,
    settings: AuthSettings,
    sender: Annotated[CodeSender, Depends(get_code_sender)],
) -> SessionView:
    """Email + password, then (when email is configured) an emailed code unless remembered.

    Without a code the response is 401 "Email code required" after mailing one (not a failed
    attempt). With the code it signs in, and may remember this browser.
    """
    user = _authenticate(db, request, settings, payload.email, payload.password)
    if not settings.email_codes_active:
        warn_fallback()
        return _issue_session(db=db, settings=settings, response=response, user=user)
    if is_trusted_device(db, request, user):
        return _issue_session(db=db, settings=settings, response=response, user=user)
    if not payload.code:
        send_code(db, request, settings, sender, user, explicit_resend=False)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=EMAIL_CODE_REQUIRED)
    guard = SignInGuard(db, request, settings, "code", payload.email)
    guard.check()
    try:
        verify_code(db, settings, user, payload.code)
    except HTTPException as exc:
        if exc.status_code == status.HTTP_401_UNAUTHORIZED:
            guard.fail()
        raise
    guard.succeed()
    if payload.remember_device:
        remember_device(db, request, response, settings, user)
    return _issue_session(db=db, settings=settings, response=response, user=user)


@router.post("/email-code/resend", status_code=status.HTTP_202_ACCEPTED)
def resend_email_code(
    payload: EmailCodeResend,
    request: Request,
    db: DB,
    settings: AuthSettings,
    sender: Annotated[CodeSender, Depends(get_code_sender)],
) -> dict[str, str]:
    """Send a new code (needs the password again). Rate limited; old codes stop working."""
    if not settings.email_codes_active:
        raise HTTPException(status_code=404, detail="Email codes are not enabled")
    user = _authenticate(db, request, settings, payload.email, payload.password)
    send_code(db, request, settings, sender, user, explicit_resend=True)
    return {"status": "accepted"}


@router.post("/magic-link", status_code=status.HTTP_202_ACCEPTED)
def request_magic_link(
    payload: MagicLinkRequest,
    request: Request,
    db: DB,
    settings: AuthSettings,
    sender: MagicSender,
) -> dict[str, str]:
    if isinstance(sender, UnconfiguredMagicLinkSender):
        raise HTTPException(status_code=503, detail="Email sign-in is not configured")
    from .reset import throttle

    email = _normalize_email(payload.email)
    ip = request.client.host if request.client else "unknown"
    if not throttle(db, [(f"magic-email:{email}", 3), (f"magic-ip:{ip}", 20)], datetime.now(UTC)):
        return {"status": "accepted"}  # same answer, no email: nothing reveals the throttle
    user = db.scalar(select(User).where(User.email == email))
    if user and user.is_active:
        token, token_hash = new_magic_link_token()
        expires = datetime.now(UTC) + timedelta(minutes=settings.magic_link_ttl_minutes)
        db.add(MagicLinkToken(user_id=user.id, token_hash=token_hash, expires_at=expires))
        db.commit()
        firm = db.get(Firm, user.firm_id) if user.firm_id else None
        sender.send(
            email=user.email,
            token=token,
            expires_at=expires,
            slug=firm.slug if firm else None,
        )
    return {"status": "accepted"}


@router.post("/magic-link/verify", response_model=SessionView)
def verify_magic_link(
    payload: MagicLinkVerify,
    request: Request,
    response: Response,
    db: DB,
    settings: AuthSettings,
) -> SessionView:
    # Locks per token and per address.
    guard = SignInGuard(db, request, settings, "magic", payload.token)
    guard.check()
    try:
        user = _verified_magic_user(db, request, payload, settings)
    except HTTPException as exc:
        if exc.status_code == status.HTTP_401_UNAUTHORIZED:
            db.rollback()
            guard.fail()
        raise
    guard.succeed()
    return _issue_session(db=db, settings=settings, response=response, user=user)


def _verified_magic_user(
    db: Session, request: Request, payload: MagicLinkVerify, settings: Settings
) -> User:
    portal = require_firm_portal(request, settings, db)
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
    # Checked before the link is consumed, so a wrong-portal attempt does not burn it.
    assert_user_on_portal(user, portal)
    record.used_at = now
    return user


@router.get("/session", response_model=SessionView)
def read_session(user: CurrentUser) -> SessionView:
    return SessionView(user=UserView.model_validate(user))


@router.post("/sign-out", status_code=status.HTTP_204_NO_CONTENT)
def sign_out(
    response: Response,
    user: AuthenticatedUser,
    db: DB,
    settings: AuthSettings,
) -> None:
    # Any portal may sign out: the session cookie is shared by every portal on the API host.
    # Revoking all current sessions is conservative and appropriate for the first release.
    for auth_session in db.scalars(
        select(AuthSession).where(AuthSession.user_id == user.id, AuthSession.revoked_at.is_(None))
    ):
        auth_session.revoked_at = datetime.now(UTC)
    db.commit()
    response.delete_cookie(
        SESSION_COOKIE,
        path="/",
        secure=settings.session_cookie_secure,
        httponly=True,
        samesite="lax",
    )


@router.post("/sign-out-others")
def sign_out_other_devices(
    request: Request,
    user: AuthenticatedUser,
    db: DB,
    settings: AuthSettings,
) -> dict[str, int]:
    """End every other session and forget every other remembered browser for this user.

    This browser's session and its remembered-device cookie (if any) stay valid.
    """
    token = request.cookies.get(SESSION_COOKIE)
    auth = request.headers.get("authorization", "")
    if not token and auth.lower().startswith("bearer "):
        token = auth[7:].strip()
    try:
        current_sid = str(decode_session_token(token or "", settings)["sid"])
    except Exception:  # noqa: BLE001 - get_authenticated_user already validated this token
        current_sid = None
    cookie = request.cookies.get(device_cookie_name(user.id))
    keep = hashlib.sha256(cookie.encode()).hexdigest() if cookie else None
    sessions = revoke_other_sessions(db, user, current_sid)
    devices = revoke_devices(
        db, user, actor=user, reason="signed_out_other_devices", keep_token_hash=keep
    )
    db.commit()
    return {"sessions_ended": sessions, "devices_forgotten": devices}
