"""Explicit demo-only walkthrough reset. Never alters credentials or ordinary users."""

import argparse

from sqlalchemy import select

from app.database.models import AuditLog, User
from app.database.session import get_session_factory

DEMO_EMAILS = ("demo-client@kiensolutions.com", "demo-auditor@kiensolutions.com")


def reset() -> int:
    with get_session_factory()() as db:
        users = db.scalars(select(User).where(User.email.in_(DEMO_EMAILS))).all()
        for user in users:
            user.onboarding_state = None
            user.onboarding_finished_at = None
            db.add(
                AuditLog(
                    firm_id=user.firm_id,
                    actor_id=None,
                    action="onboarding.demo_reset",
                    entity_type="user",
                    entity_id=user.id,
                    details={"synthetic": True},
                )
            )
        db.commit()
        return len(users)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset-demo", action="store_true", required=True)
    parser.parse_args()
    print(f"Reset {reset()} synthetic demo walkthroughs")
