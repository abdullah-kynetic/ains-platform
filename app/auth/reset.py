"""Single-use password recovery with database-backed throttling."""

import hashlib
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.auth.email import ResendSender
from app.auth.email_code import revoke_devices
from app.auth.security import hash_magic_link_token, hash_password, new_magic_link_token
from app.config import Settings, get_settings
from app.database.models import (
    AuthRateLimit,
    AuthSession,
    Firm,
    MagicLinkToken,
    PasswordResetToken,
    User,
)
from app.database.session import get_db

router = APIRouter(prefix="/auth/password-reset", tags=["auth"])
DB = Annotated[Session, Depends(get_db)]
Config = Annotated[Settings, Depends(get_settings)]


class ResetRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)


class ResetConfirm(BaseModel):
    token: str = Field(min_length=20, max_length=512)
    password: str = Field(min_length=12, max_length=1024)


def throttle(db: Session, identities: list[tuple[str, int]], now: datetime) -> bool:
    allowed = True
    # Serialize creation and increments on Postgres, including absent rows.
    if db.bind.dialect.name == "postgresql":
        from sqlalchemy import text

        db.execute(text("SELECT pg_advisory_xact_lock(1093310)"))
    for identity, limit in identities:
        key = hashlib.sha256(identity.encode()).hexdigest()
        row = db.get(AuthRateLimit, key, with_for_update=True)
        if row is None:
            row = AuthRateLimit(key=key, count=0, window_start=now)
            db.add(row)
        if row.window_start.replace(tzinfo=UTC) < now - timedelta(hours=1):
            row.count = 0
            row.window_start = now
        row.count += 1
        allowed = allowed and row.count <= limit
    db.commit()
    return allowed


@router.post("/request", status_code=202)
def request_reset(
    payload: ResetRequest, request: Request, db: DB, settings: Config
) -> dict[str, str]:
    if not settings.resend_api_key.get_secret_value() or not settings.email_from:
        raise HTTPException(status_code=503, detail="Email delivery is not configured")
    now = datetime.now(UTC)
    email = payload.email.strip().casefold()
    accepted = {"status": "accepted"}
    if not throttle(
        db,
        [
            (f"reset-email:{email}", 3),
            (f"reset-ip:{request.client.host if request.client else 'unknown'}", 20),
        ],
        now,
    ):
        return accepted
    user = db.scalar(select(User).where(User.email == email, User.is_active.is_(True)))
    if user:
        token, digest = new_magic_link_token()
        expires = now + timedelta(minutes=settings.password_reset_ttl_minutes)
        db.add(PasswordResetToken(user_id=user.id, token_hash=digest, expires_at=expires))
        db.commit()
        try:
            firm = db.get(Firm, user.firm_id) if user.firm_id else None
            ResendSender(settings, "reset").send(
                email=email, token=token, expires_at=expires, slug=firm.slug if firm else None
            )
        except HTTPException:
            # Keep the same response for registered and unregistered addresses.
            pass
    return accepted


@router.post("/confirm")
def confirm_reset(payload: ResetConfirm, db: DB) -> dict[str, str]:
    now = datetime.now(UTC)
    record = db.scalar(
        select(PasswordResetToken).where(
            PasswordResetToken.token_hash == hash_magic_link_token(payload.token),
            PasswordResetToken.used_at.is_(None),
        )
    )
    if not record or record.expires_at.replace(tzinfo=UTC) <= now:
        raise HTTPException(status_code=400, detail="Reset link is invalid or expired")
    # Lock the user before claiming tokens, so concurrent reset links for one user
    # cannot deadlock when invalidating the other outstanding tokens.
    user = db.get(User, record.user_id, with_for_update=True)
    if not user or not user.is_active:
        raise HTTPException(status_code=400, detail="Reset link is invalid or expired")
    # Atomic claim also protects single-use behavior on databases without row locks.
    claimed = db.execute(
        update(PasswordResetToken)
        .where(
            PasswordResetToken.id == record.id,
            PasswordResetToken.used_at.is_(None),
            PasswordResetToken.expires_at > datetime.now(UTC),
        )
        .values(used_at=now)
        .execution_options(synchronize_session=False)
    )
    if claimed.rowcount != 1:
        raise HTTPException(status_code=400, detail="Reset link is invalid or expired")
    user.password_hash = hash_password(payload.password)
    db.execute(update(AuthSession).where(AuthSession.user_id == user.id).values(revoked_at=now))
    # A changed password also forgets remembered browsers, so the next sign-in needs a code.
    revoke_devices(db, user, actor=user, reason="password_reset")
    for model in (PasswordResetToken, MagicLinkToken):
        db.execute(
            update(model)
            .where(model.user_id == user.id, model.used_at.is_(None))
            .values(used_at=now)
        )
    db.commit()
    return {"status": "password_updated"}
