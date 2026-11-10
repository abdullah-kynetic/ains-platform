"""Invalidate stale identity scopes and enforce auditor MFA on every authenticated request."""

from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import event, inspect, update
from sqlalchemy.orm import Session

from app.database.models import AuditLog, AuthSession, User, UserRole


def assert_session_identity(
    payload: dict[str, object], user: User, *, require_mfa: bool = True
) -> None:
    # Older tokens without bound identity claims require a fresh sign-in.
    if payload.get("role") != user.role.value or payload.get("firm_id") != user.firm_id:
        raise HTTPException(401, "Session is invalid or expired")
    if (
        require_mfa
        and user.role == UserRole.AUDITOR
        and (not user.mfa_enabled or not user.mfa_secret)
    ):
        raise HTTPException(403, "Auditor MFA enrollment is required")


@event.listens_for(Session, "before_flush", insert=True)
def revoke_changed_identity_sessions(db: Session, _context: object, _instances: object) -> None:
    """Revoke ORM identity changes atomically, before the audit chain hashes new events.

    JWT identity checks also refuse out-of-band role/firm updates. The team API must
    record its actual actor separately; this system event does not invent an actor.
    """
    for user in tuple(db.dirty):
        if not isinstance(user, User):
            continue
        state = inspect(user)
        if not any(state.attrs[field].history.has_changes() for field in ("role", "firm_id")):
            continue
        db.execute(
            update(AuthSession)
            .where(
                AuthSession.user_id == user.id,
                AuthSession.revoked_at.is_(None),
            )
            .values(revoked_at=datetime.now(UTC))
            .execution_options(synchronize_session=False)
        )
        db.add(
            AuditLog(
                firm_id=user.firm_id,
                action="auth.sessions_revoked",
                entity_type="user",
                entity_id=user.id,
                details={"reason": "identity_scope_changed"},
            )
        )
