"""S-06: expired, revoked, identity-changed and legacy tokens are refused."""

from datetime import UTC, datetime, timedelta

import jwt
import pytest
from sqlalchemy import select

from app.audit import verify
from app.auth.security import create_session_token, new_magic_link_token
from app.config import get_settings
from app.database.models import AuditLog, AuthSession, PasswordResetToken, User, UserRole
from tests.test_backend_api import sign_in_client


def test_expired_token_and_revoked_session_return_401(backend):
    client, factory, ids, *_ = backend
    sign_in_client(client)
    settings = client.app.dependency_overrides[get_settings]()
    current = client.cookies.get("ains_session")
    with factory() as db:
        row = db.scalar(select(AuthSession).where(AuthSession.user_id == ids["client_a"]))
        expired = create_session_token(
            user_id=ids["client_a"],
            session_id=row.id,
            role="client",
            firm_id=ids["firm_a"],
            settings=settings,
            now=datetime.now(UTC) - timedelta(hours=13),
        )
        session_id = row.id
    client.cookies.clear()
    assert (
        client.get("/auth/session", headers={"Authorization": f"Bearer {expired}"}).status_code
        == 401
    )
    assert (
        client.get("/auth/session", headers={"Authorization": f"Bearer {current}"}).status_code
        == 200
    )
    with factory() as db:
        db.get(AuthSession, session_id).revoked_at = datetime.now(UTC)
        db.commit()
    response = client.get("/auth/session", headers={"Authorization": f"Bearer {current}"})
    assert response.status_code == 401


@pytest.mark.parametrize("field", ["role", "firm_id"])
def test_identity_changes_revoke_sessions_atomically_and_audit(backend, field):
    client, factory, ids, *_ = backend
    sign_in_client(client)
    with factory() as db:
        user = db.get(User, ids["client_a"])
        setattr(user, field, UserRole.AUDITOR if field == "role" else ids["firm_b"])
        db.commit()
        assert all(
            row.revoked_at is not None
            for row in db.scalars(select(AuthSession).where(AuthSession.user_id == user.id))
        )
        logs = db.scalars(
            select(AuditLog).where(AuditLog.firm_id == user.firm_id).order_by(AuditLog.sequence)
        ).all()
        assert verify(logs)["valid"]
        assert any(row.action == "auth.sessions_revoked" for row in logs)
    assert client.get("/auth/session").status_code == 401


def test_signout_revokes_sid_and_legacy_identity_claims_require_reauthentication(backend):
    client, factory, ids, *_ = backend
    sign_in_client(client)
    settings = client.app.dependency_overrides[get_settings]()
    token = client.cookies.get("ains_session")
    payload = jwt.decode(token, settings.session_secret.get_secret_value(), algorithms=["HS256"])
    payload.pop("role")
    legacy = jwt.encode(payload, settings.session_secret.get_secret_value(), algorithm="HS256")
    client.cookies.clear()
    assert (
        client.get("/auth/session", headers={"Authorization": f"Bearer {legacy}"}).status_code
        == 401
    )
    assert (
        client.get("/auth/session", headers={"Authorization": f"Bearer {token}"}).status_code == 200
    )
    assert (
        client.post("/auth/sign-out", headers={"Authorization": f"Bearer {token}"}).status_code
        == 204
    )
    response = client.get("/auth/session", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


def test_database_expiry_is_checked_even_when_jwt_has_not_expired(backend):
    client, factory, ids, *_ = backend
    sign_in_client(client)
    with factory() as db:
        row = db.scalar(select(AuthSession).where(AuthSession.user_id == ids["client_a"]))
        row.expires_at = datetime.now(UTC) - timedelta(seconds=1)
        db.commit()
    assert client.get("/auth/session").status_code == 401


def test_role_change_rollback_does_not_revoke_a_committed_session(backend):
    client, factory, ids, *_ = backend
    sign_in_client(client)
    with factory() as db:
        db.get(User, ids["client_a"]).role = UserRole.AUDITOR
        db.flush()
        db.rollback()
    assert client.get("/auth/session").status_code == 200


def test_password_reset_revokes_all_own_sessions_and_preserves_other_users(backend):
    client, factory, ids, *_ = backend
    sign_in_client(client)
    token, digest = new_magic_link_token()
    with factory() as db:
        expiry = datetime.now(UTC) + timedelta(hours=1)
        other = AuthSession(user_id=ids["client_b"], expires_at=expiry)
        db.add_all(
            [
                other,
                AuthSession(user_id=ids["client_a"], expires_at=expiry),
                PasswordResetToken(user_id=ids["client_a"], token_hash=digest, expires_at=expiry),
            ]
        )
        db.commit()
        other_id = other.id
    response = client.post(
        "/auth/password-reset/confirm",
        json={
            "token": token,
            "password": "synthetic-replacement-password",
        },
    )
    assert response.status_code == 200
    assert client.get("/auth/session").status_code == 401
    with factory() as db:
        assert all(
            row.revoked_at is not None
            for row in db.scalars(select(AuthSession).where(AuthSession.user_id == ids["client_a"]))
        )
        assert db.get(AuthSession, other_id).revoked_at is None
