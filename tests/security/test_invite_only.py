"""S-05: no registration route; invitations expire and are consumed once."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select

from app.auth.security import new_invitation_token
from app.database.models import ClientInvitation, User


def test_unknown_password_login_cannot_register_a_user(backend):
    client, factory, *_ = backend
    paths = client.app.openapi()["paths"]
    assert not any(
        word in path.lower() for path in paths for word in ("sign-up", "signup", "register")
    )
    with factory() as db:
        before = db.scalar(select(func.count()).select_from(User))
    response = client.post(
        "/auth/password",
        json={
            "email": "not-invited@example.test",
            "password": "synthetic-password-only",
        },
    )
    assert response.status_code == 401 and "set-cookie" not in response.headers
    with factory() as db:
        assert db.scalar(select(func.count()).select_from(User)) == before


def test_invites_expire_and_cannot_be_replayed(backend):
    client, factory, ids, *_ = backend
    valid, digest = new_invitation_token()
    expired, expired_digest = new_invitation_token()
    with factory() as db:
        for email, token_hash, delta in (
            ("invited@example.test", digest, 1),
            ("expired@example.test", expired_digest, -1),
        ):
            db.add(
                ClientInvitation(
                    firm_id=ids["firm_a"],
                    engagement_id=ids["engagement_a"],
                    created_by_id=ids["auditor"],
                    name="Synthetic Invite",
                    email=email,
                    token_hash=token_hash,
                    expires_at=datetime.now(UTC) + timedelta(hours=delta),
                )
            )
        db.commit()

    def accept(token):
        return client.post(
            "/auth/invitations/accept",
            json={
                "token": token,
                "password": "synthetic-invited-password",
            },
        )

    rejected = accept(expired)
    assert rejected.status_code == 410 and "set-cookie" not in rejected.headers
    assert accept(valid).status_code == 200
    client.cookies.clear()
    rejected = accept(valid)
    assert rejected.status_code == 410 and "set-cookie" not in rejected.headers
    with factory() as db:
        assert db.scalar(select(User).where(User.email == "expired@example.test")) is None
        assert len(db.scalars(select(User).where(User.email == "invited@example.test")).all()) == 1
