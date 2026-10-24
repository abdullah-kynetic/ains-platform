"""Invite-only password and magic-link sign-in endpoints.

Magic-link delivery is intentionally an injectable boundary. The default sender records no
token and emits no logs; deployment must supply an email delivery adapter before enabling that
method. Tests inject a capture sender without exposing real credentials.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Annotated, Protocol

import pyotp
from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.database.models import (
    AuditLog,
    AuthSession,
    MagicLinkToken,
    MFARecoveryCode,
    User,
    UserRole,
)
from app.database.session import get_db

from .dependencies import SESSION_COOKIE, get_current_user
from .security import (
    create_session_token,
    hash_magic_link_token,
    hash_mfa_recovery_code,
    new_magic_link_token,
    new_mfa_recovery_code,
    new_totp_secret,
    verify_password,
    verify_totp,
)

router = APIRouter(prefix="/auth", tags=["auth"])
DB = Annotated[Session, Depends(get_db)]
AuthSettings = Annotated[Settings, Depends(get_settings)]


class PasswordSignIn(BaseModel):
    email: str
    password: str = Field(min_length=8, max_length=1024)
    mfa_code: str | None = Field(default=None, min_length=6, max_length=32)


class MagicLinkRequest(BaseModel):
    email: str


class MagicLinkVerify(BaseModel):
    token: str = Field(min_length=20, max_length=512)
    mfa_code: str | None = Field(default=None, min_length=6, max_length=32)


class AuditorMFAStart(BaseModel):
    email: str
    password: str = Field(min_length=8, max_length=1024)


class AuditorMFAConfirm(AuditorMFAStart):
    code: str = Field(min_length=6, max_length=8)


class AuditorMFARecoveryRotate(BaseModel):
    code: str = Field(min_length=6, max_length=8)


class UserView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    name: str
    role: UserRole
    firm_id: str | None


class SessionView(BaseModel):
    user: UserView


class AuditorMFAEnrollmentView(BaseModel):
    secret: str
    provisioning_uri: str
    expires_at: datetime


class AuditorMFAEnrollmentComplete(SessionView):
    recovery_codes: list[str]


class AuditorMFARecoveryCodes(BaseModel):
    recovery_codes: list[str]


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


@router.get("/capabilities")
def auth_capabilities(settings: AuthSettings, sender: MagicSender) -> dict[str, bool]:
    configured = len(settings.session_secret.get_secret_value().encode()) >= 32
    return {
        "password_sign_in": configured,
        "magic_link": configured and not isinstance(sender, UnconfiguredMagicLinkSender),
    }


def _normalize_email(email: str) -> str:
    return email.strip().casefold()


def _require_auditor_mfa(db: Session, user: User, code: str | None) -> None:
    if user.role != UserRole.AUDITOR:
        return
    if not user.mfa_enabled or not user.mfa_secret:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Auditor MFA enrollment is required",
        )
    if not code:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="MFA code required")
    if verify_totp(user.mfa_secret, code):
        return
    recovery_code = db.scalar(
        select(MFARecoveryCode)
        .where(
            MFARecoveryCode.user_id == user.id,
            MFARecoveryCode.code_hash == hash_mfa_recovery_code(code or ""),
            MFARecoveryCode.used_at.is_(None),
            MFARecoveryCode.revoked_at.is_(None),
        )
        .with_for_update()
    )
    if recovery_code is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid MFA code")
    recovery_code.used_at = datetime.now(UTC)
    db.add(
        AuditLog(
            actor_id=user.id,
            action="auth.mfa_recovery_code_used",
            entity_type="user",
            entity_id=user.id,
        )
    )


def _password_user(db: Session, email: str, password: str) -> User:
    user = db.scalar(select(User).where(User.email == _normalize_email(email)))
    if not user or not user.is_active or not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password"
        )
    return user


def _new_recovery_codes(db: Session, user: User) -> list[str]:
    now = datetime.now(UTC)
    for record in db.scalars(
        select(MFARecoveryCode).where(
            MFARecoveryCode.user_id == user.id,
            MFARecoveryCode.used_at.is_(None),
            MFARecoveryCode.revoked_at.is_(None),
        )
    ):
        record.revoked_at = now
    codes = [new_mfa_recovery_code() for _ in range(10)]
    db.add_all(
        [
            MFARecoveryCode(user_id=user.id, code_hash=hash_mfa_recovery_code(code))
            for code in codes
        ]
    )
    return codes


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
    user = _password_user(db, payload.email, payload.password)
    _require_auditor_mfa(db, user, payload.mfa_code)
    return _issue_session(db=db, settings=settings, response=response, user=user)


@router.post("/auditor/mfa/enrollment", response_model=AuditorMFAEnrollmentView)
def start_auditor_mfa_enrollment(
    payload: AuditorMFAStart,
    db: DB,
    settings: AuthSettings,
) -> AuditorMFAEnrollmentView:
    user = _password_user(db, payload.email, payload.password)
    if user.role != UserRole.AUDITOR:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Auditor access required")
    if user.mfa_enabled:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="MFA is already enabled")

    now = datetime.now(UTC)
    secret = new_totp_secret()
    user.mfa_secret = secret
    user.mfa_enrollment_expires_at = now + timedelta(
        minutes=settings.auditor_mfa_enrollment_ttl_minutes
    )
    db.add(
        AuditLog(
            actor_id=user.id,
            action="auth.mfa_enrollment_started",
            entity_type="user",
            entity_id=user.id,
        )
    )
    db.commit()
    return AuditorMFAEnrollmentView(
        secret=secret,
        provisioning_uri=pyotp.TOTP(secret).provisioning_uri(
            name=user.email,
            issuer_name=settings.auditor_mfa_issuer,
        ),
        expires_at=user.mfa_enrollment_expires_at,
    )


@router.post("/auditor/mfa/enrollment/confirm", response_model=AuditorMFAEnrollmentComplete)
def confirm_auditor_mfa_enrollment(
    payload: AuditorMFAConfirm,
    response: Response,
    db: DB,
    settings: AuthSettings,
) -> AuditorMFAEnrollmentComplete:
    user = _password_user(db, payload.email, payload.password)
    if user.role != UserRole.AUDITOR:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Auditor access required")
    if user.mfa_enabled:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="MFA is already enabled")
    now = datetime.now(UTC)
    if (
        not user.mfa_secret
        or not user.mfa_enrollment_expires_at
        or (
            user.mfa_enrollment_expires_at.replace(tzinfo=UTC)
            if not user.mfa_enrollment_expires_at.tzinfo
            else user.mfa_enrollment_expires_at
        )
        <= now
    ):
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="MFA enrollment has expired")
    if not verify_totp(user.mfa_secret, payload.code):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid MFA code")

    user.mfa_enabled = True
    user.mfa_enrollment_expires_at = None
    recovery_codes = _new_recovery_codes(db, user)
    db.add(
        AuditLog(
            actor_id=user.id,
            action="auth.mfa_enrollment_completed",
            entity_type="user",
            entity_id=user.id,
        )
    )
    session = _issue_session(db=db, settings=settings, response=response, user=user)
    return AuditorMFAEnrollmentComplete(
        user=session.user,
        recovery_codes=recovery_codes,
    )


@router.post("/auditor/mfa/recovery-codes", response_model=AuditorMFARecoveryCodes)
def rotate_auditor_mfa_recovery_codes(
    payload: AuditorMFARecoveryRotate,
    user: CurrentUser,
    db: DB,
) -> AuditorMFARecoveryCodes:
    if user.role != UserRole.AUDITOR:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Auditor access required")
    if not user.mfa_enabled or not verify_totp(user.mfa_secret, payload.code):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid MFA code")
    recovery_codes = _new_recovery_codes(db, user)
    db.add(
        AuditLog(
            actor_id=user.id,
            action="auth.mfa_recovery_codes_rotated",
            entity_type="user",
            entity_id=user.id,
        )
    )
    db.commit()
    return AuditorMFARecoveryCodes(recovery_codes=recovery_codes)


@router.post("/magic-link", status_code=status.HTTP_202_ACCEPTED)
def request_magic_link(
    payload: MagicLinkRequest,
    db: DB,
    settings: AuthSettings,
    sender: MagicSender,
) -> dict[str, str]:
    if isinstance(sender, UnconfiguredMagicLinkSender):
        raise HTTPException(status_code=503, detail="Email sign-in is not configured")
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
    _require_auditor_mfa(db, user, payload.mfa_code)
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
