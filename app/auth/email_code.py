"""Emailed 6-digit sign-in codes and remembered browsers (replaces the authenticator app).

Flow: email + password, then (when email delivery is configured) a code by email. A correct code can
remember the browser for ``trusted_device_days`` with an httpOnly cookie. Codes are stored only as
keyed hashes, expire, are single use, burn after a few wrong guesses and are rate limited. Every
step is audit-logged without the code. With no email key configured the step is skipped (logged).
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import secrets
from datetime import UTC, datetime, timedelta
from typing import Annotated, Protocol

from fastapi import Depends, HTTPException, Request, Response, status
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.database.models import (
    AuditLog,
    AuthSession,
    EmailSignInCode,
    TrustedDevice,
    User,
)

from .email import ResendCodeSender

logger = logging.getLogger(__name__)

EMAIL_CODE_REQUIRED = "Email code required"
INVALID_CODE = "Code is invalid or expired"


class CodeSender(Protocol):
    def send(self, *, email: str, code: str, expires_at: datetime) -> None: ...


def get_code_sender(settings: Annotated[Settings, Depends(get_settings)]) -> CodeSender:
    return ResendCodeSender(settings)


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=UTC)


def _audit(db: Session, user: User, action: str, **details: object) -> None:
    db.add(
        AuditLog(
            firm_id=user.firm_id,
            actor_id=user.id,
            action=action,
            entity_type="user",
            entity_id=user.id,
            details=dict(details),
        )
    )


def hash_code(settings: Settings, user: User, code: str) -> str:
    key = settings.session_secret.get_secret_value().encode()
    return hmac.new(key, f"{user.id}:{code}".encode(), hashlib.sha256).hexdigest()


def new_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def normalize_code(code: str) -> str:
    return "".join(code.split())


def warn_fallback() -> None:
    logger.warning(
        "Email sign-in codes are OFF: RESEND_API_KEY / EMAIL_FROM are not set (or "
        "EMAIL_SIGN_IN_CODES=false). Signing in with email + password only. "
        "Do not run production like this."
    )


# --- sending -----------------------------------------------------------------------------


def _latest_live_code(db: Session, user: User, now: datetime) -> EmailSignInCode | None:
    record = db.scalar(
        select(EmailSignInCode)
        .where(
            EmailSignInCode.user_id == user.id,
            EmailSignInCode.used_at.is_(None),
            EmailSignInCode.revoked_at.is_(None),
        )
        .order_by(EmailSignInCode.created_at.desc())
        .limit(1)
    )
    if record is not None and _aware(record.expires_at) > now:
        return record
    return None


def send_code(
    db: Session,
    request: Request,
    settings: Settings,
    sender: CodeSender,
    user: User,
    *,
    explicit_resend: bool,
) -> None:
    """Email a fresh code. Without ``explicit_resend`` a code sent moments ago is not re-sent."""
    from .reset import throttle  # lazy: reset imports this module

    now = datetime.now(UTC)
    live = _latest_live_code(db, user, now)
    cooldown = timedelta(seconds=settings.email_code_resend_seconds)
    if live is not None and _aware(live.created_at) + cooldown > now:
        if not explicit_resend:
            return
        wait = int((_aware(live.created_at) + cooldown - now).total_seconds()) + 1
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Wait a moment before asking for another code.",
            headers={"Retry-After": str(max(wait, 1))},
        )
    ip = request.client.host if request.client else "unknown"
    allowed = throttle(
        db,
        [
            (f"code-send:{user.id}", settings.email_code_max_sends_per_hour),
            (f"code-send-ip:{ip}", settings.email_code_max_sends_per_hour * 4),
        ],
        now,
    )
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many codes requested. Try again later.",
            headers={"Retry-After": "3600"},
        )
    for old in db.scalars(
        select(EmailSignInCode).where(
            EmailSignInCode.user_id == user.id,
            EmailSignInCode.used_at.is_(None),
            EmailSignInCode.revoked_at.is_(None),
        )
    ):
        old.revoked_at = now
    code = new_code()
    expires = now + timedelta(minutes=settings.email_code_ttl_minutes)
    db.add(
        EmailSignInCode(
            user_id=user.id,
            firm_id=user.firm_id,
            code_hash=hash_code(settings, user, code),
            expires_at=expires,
        )
    )
    db.flush()
    try:
        sender.send(email=user.email, code=code, expires_at=expires)
    except HTTPException:
        db.rollback()
        raise
    _audit(db, user, "auth.email_code_sent", resend=explicit_resend)
    db.commit()


# --- verifying ---------------------------------------------------------------------------


def _fail(db: Session, user: User, reason: str) -> HTTPException:
    _audit(db, user, "auth.email_code_failed", reason=reason)
    db.commit()
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=INVALID_CODE)


def verify_code(db: Session, settings: Settings, user: User, raw_code: str) -> None:
    """Accept a correct, live, unused code exactly once; raise 401 otherwise (audit-logged)."""
    now = datetime.now(UTC)
    code = normalize_code(raw_code)
    record = db.scalar(
        select(EmailSignInCode)
        .where(
            EmailSignInCode.user_id == user.id,
            EmailSignInCode.used_at.is_(None),
            EmailSignInCode.revoked_at.is_(None),
        )
        .order_by(EmailSignInCode.created_at.desc())
        .limit(1)
        .with_for_update()
    )
    if record is None or record.firm_id != user.firm_id:
        raise _fail(db, user, "no_active_code")
    if _aware(record.expires_at) <= now:
        raise _fail(db, user, "expired")
    if record.attempts >= settings.email_code_max_attempts:
        raise _fail(db, user, "too_many_attempts")
    record.attempts += 1
    if not hmac.compare_digest(record.code_hash, hash_code(settings, user, code)):
        if record.attempts >= settings.email_code_max_attempts:
            record.revoked_at = now  # burned: a new code must be requested
        raise _fail(db, user, "wrong_code")
    # Atomic claim: two concurrent requests with the same code cannot both succeed.
    claimed = db.execute(
        update(EmailSignInCode)
        .where(EmailSignInCode.id == record.id, EmailSignInCode.used_at.is_(None))
        .values(used_at=now)
        .execution_options(synchronize_session=False)
    )
    if claimed.rowcount != 1:
        raise _fail(db, user, "reused")
    _audit(db, user, "auth.email_code_accepted")
    # Committed with the session that follows; the caller commits.


# --- remembered browsers -----------------------------------------------------------------


def device_cookie_name(user_id: str) -> str:
    """One cookie per user, so two people on one browser do not overwrite each other."""
    return "kien_device_" + hashlib.sha256(user_id.encode()).hexdigest()[:12]


def _device_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def is_trusted_device(db: Session, request: Request, user: User) -> bool:
    token = request.cookies.get(device_cookie_name(user.id))
    if not token:
        return False
    device = db.scalar(
        select(TrustedDevice).where(
            TrustedDevice.token_hash == _device_hash(token),
            TrustedDevice.user_id == user.id,
            TrustedDevice.firm_id.is_(None)
            if user.firm_id is None
            else TrustedDevice.firm_id == user.firm_id,
            TrustedDevice.revoked_at.is_(None),
        )
    )
    now = datetime.now(UTC)
    if device is None or _aware(device.expires_at) <= now:
        return False
    device.last_used_at = now
    return True


def remember_device(
    db: Session, request: Request, response: Response, settings: Settings, user: User
) -> None:
    now = datetime.now(UTC)
    token = secrets.token_urlsafe(32)
    days = settings.trusted_device_days
    device = TrustedDevice(
        user_id=user.id,
        firm_id=user.firm_id,
        token_hash=_device_hash(token),
        user_agent=(request.headers.get("user-agent") or "")[:200] or None,
        expires_at=now + timedelta(days=days),
        last_used_at=now,
    )
    db.add(device)
    db.flush()
    _audit(db, user, "auth.device_remembered", device_id=device.id, days=days)
    response.set_cookie(
        device_cookie_name(user.id),
        token,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
        max_age=days * 86400,
        path="/auth",
    )


def revoke_devices(
    db: Session,
    user: User,
    *,
    actor: User,
    reason: str,
    keep_token_hash: str | None = None,
) -> int:
    """Revoke a user's remembered browsers (all, or all but one). Caller commits."""
    now = datetime.now(UTC)
    query = select(TrustedDevice).where(
        TrustedDevice.user_id == user.id, TrustedDevice.revoked_at.is_(None)
    )
    count = 0
    for device in db.scalars(query):
        if keep_token_hash and device.token_hash == keep_token_hash:
            continue
        device.revoked_at = now
        count += 1
    if count:
        db.add(
            AuditLog(
                firm_id=user.firm_id,
                actor_id=actor.id,
                action="auth.device_revoked",
                entity_type="user",
                entity_id=user.id,
                details={"reason": reason, "count": count},
            )
        )
    return count


def revoke_other_sessions(db: Session, user: User, keep_session_id: str | None) -> int:
    now = datetime.now(UTC)
    count = 0
    for auth_session in db.scalars(
        select(AuthSession).where(AuthSession.user_id == user.id, AuthSession.revoked_at.is_(None))
    ):
        if auth_session.id != keep_session_id:
            auth_session.revoked_at = now
            count += 1
    return count
