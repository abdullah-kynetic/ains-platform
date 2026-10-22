"""Password, MFA, magic-link, and signed-session primitives."""

from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta

import jwt
import pyotp
from pwdlib import PasswordHash

from app.config import Settings

PASSWORD_HASH = PasswordHash.recommended()
JWT_ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return PASSWORD_HASH.hash(password)


def verify_password(password: str, password_hash: str | None) -> bool:
    return bool(password_hash) and PASSWORD_HASH.verify(password, password_hash)


def verify_totp(secret: str | None, code: str | None) -> bool:
    return bool(secret and code and pyotp.TOTP(secret).verify(code, valid_window=1))


def new_magic_link_token() -> tuple[str, str]:
    token = secrets.token_urlsafe(32)
    return token, hashlib.sha256(token.encode()).hexdigest()


def hash_magic_link_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_session_token(
    *, user_id: str, session_id: str, settings: Settings, now: datetime | None = None
) -> str:
    secret = settings.session_secret.get_secret_value()
    if not secret:
        raise RuntimeError("SESSION_SECRET is not configured")
    issued = now or datetime.now(UTC)
    expires = issued + timedelta(hours=settings.session_ttl_hours)
    return jwt.encode(
        {"sub": user_id, "sid": session_id, "iat": issued, "exp": expires},
        secret,
        algorithm=JWT_ALGORITHM,
    )


def decode_session_token(token: str, settings: Settings) -> dict[str, object]:
    secret = settings.session_secret.get_secret_value()
    if not secret:
        raise RuntimeError("SESSION_SECRET is not configured")
    return jwt.decode(token, secret, algorithms=[JWT_ALGORITHM])
