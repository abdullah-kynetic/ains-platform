"""Local backend for the web sign-in end-to-end test. SYNTHETIC data and test-only secrets.

Starts the real FastAPI app on a throwaway SQLite file with a few synthetic users, so the
browser test exercises the real /auth/* routes. Never point this at a real database.

    uv run python scripts/e2e_backend.py [--port 8000] [--db /tmp/kien-e2e.db]
"""

import argparse
import os
import sys
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

PORT_DEFAULT = 8000
ORIGIN = "http://kynetic.localhost:3100"
MFA_SECRET = "JBSWY3DPEHPK3PXP"  # synthetic TOTP secret, test only
CLIENT_PASSWORD = "synthetic-client-password"
AUDITOR_PASSWORD = "synthetic-auditor-password"
INVITE_TOKEN = "synthetic-invitation-token-0123456789abcdef"
USERS = {
    "client": "e2e-client@example.test",
    "lockout": "e2e-lockout@example.test",
    "auditor": "e2e-auditor@example.test",
    "invitee": "e2e-invitee@example.test",
}


def configure(db_path: Path) -> None:
    os.environ["DATABASE_URL"] = f"sqlite+pysqlite:///{db_path}"
    os.environ["SESSION_SECRET"] = "synthetic-e2e-session-secret-not-for-real-use-0000"
    os.environ["SESSION_COOKIE_SECURE"] = "false"
    os.environ["CORS_ORIGINS"] = ORIGIN
    os.environ["PORTAL_URL"] = ORIGIN


def seed() -> None:
    from app.auth.security import hash_invitation_token, hash_password
    from app.database.models import (
        Base,
        ClientInvitation,
        Engagement,
        Firm,
        User,
        UserRole,
    )
    from app.database.session import get_engine, get_session_factory

    Base.metadata.create_all(get_engine())
    now = datetime.now(UTC)
    with get_session_factory()() as db:
        firm = Firm(name="Synthetic E2E Securities", slug="synthetic-e2e")
        db.add(firm)
        db.flush()
        auditor = User(
            email=USERS["auditor"],
            name="Synthetic E2E Auditor",
            role=UserRole.AUDITOR,
            password_hash=hash_password(AUDITOR_PASSWORD),
            mfa_secret=MFA_SECRET,
            mfa_enabled=True,
            accepted_at=now,
        )
        db.add(auditor)
        for key in ("client", "lockout"):
            db.add(
                User(
                    firm_id=firm.id,
                    email=USERS[key],
                    name=f"Synthetic E2E {key.title()}",
                    role=UserRole.CLIENT,
                    password_hash=hash_password(CLIENT_PASSWORD),
                    accepted_at=now,
                )
            )
        db.flush()
        engagement = Engagement(
            firm_id=firm.id,
            auditor_id=auditor.id,
            review_period_start=date(2025, 1, 1),
            review_period_end=date(2025, 12, 31),
        )
        db.add(engagement)
        db.flush()
        db.add(
            ClientInvitation(
                firm_id=firm.id,
                engagement_id=engagement.id,
                email=USERS["invitee"],
                name="Synthetic E2E Invitee",
                token_hash=hash_invitation_token(INVITE_TOKEN),
                expires_at=now + timedelta(days=3),
                created_by_id=auditor.id,
            )
        )
        db.commit()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=PORT_DEFAULT)
    parser.add_argument("--db", type=Path, default=Path("/tmp/kien-e2e.db"))
    args = parser.parse_args()
    if "postgres" in os.environ.get("DATABASE_URL", ""):
        sys.exit("Refusing to run: DATABASE_URL points at Postgres. This script is synthetic-only.")
    args.db.unlink(missing_ok=True)
    configure(args.db)
    seed()
    import uvicorn

    uvicorn.run("app.main:app", host="127.0.0.1", port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
