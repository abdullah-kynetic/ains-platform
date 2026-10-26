"""Idempotent report seed for the existing explicitly synthetic demo engagement."""

from sqlalchemy import select

from app.database.models import Engagement, Firm, User, UserRole
from app.database.session import get_session_factory
from app.reports.workflow import create_report

DEMO_EMAIL = "demo-auditor@kiensolutions.com"


def seed() -> str:
    with get_session_factory()() as db:
        user = db.scalar(
            select(User).where(User.email == DEMO_EMAIL, User.role == UserRole.AUDITOR)
        )
        if not user:
            raise RuntimeError("Existing synthetic demo auditor required")
        engagement = db.scalar(
            select(Engagement)
            .join(Firm)
            .where(
                Engagement.auditor_id == user.id,
                (Firm.name.ilike("%synthetic%") | Firm.slug.ilike("%synthetic%")),
            )
            .order_by(Engagement.id)
            .limit(1)
        )
        if not engagement:
            raise RuntimeError("Explicitly synthetic assigned engagement required")
        report = create_report(db, engagement, user)
        db.commit()
        return report.id


if __name__ == "__main__":
    print(f"Synthetic report: {seed()}")
