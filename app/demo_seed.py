"""Idempotently load one synthetic demo firm, users and engagement.

Mock data only: never point this at a database holding real client records.
Run inside the API image: ``python -m app.demo_seed`` (optional ``DEMO_PASSWORD``
sets a sign-in password for both synthetic users).
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import select

from app.auth.security import hash_password
from app.checklist.catalog import initialize_engagement
from app.config import get_settings
from app.database.models import Engagement, Firm, User, UserRole
from app.database.session import get_session_factory

FIRM_SLUG = "demo-synthetic-bd"
AUDITOR_EMAIL = "demo-auditor@example.com"
CLIENT_EMAIL = "demo-client@example.com"


def seed() -> str:
    password = get_settings().demo_password.get_secret_value() or None
    with get_session_factory()() as session:
        firm = session.scalar(select(Firm).where(Firm.slug == FIRM_SLUG))
        if firm is None:
            firm = Firm(name="Demo Broker-Dealer LLC (synthetic)", slug=FIRM_SLUG)
            session.add(firm)
            session.flush()
        auditor = session.scalar(select(User).where(User.email == AUDITOR_EMAIL))
        if auditor is None:
            auditor = User(email=AUDITOR_EMAIL, name="Demo Auditor", role=UserRole.AUDITOR)
            session.add(auditor)
        client = session.scalar(select(User).where(User.email == CLIENT_EMAIL))
        if client is None:
            client = User(
                firm_id=firm.id, email=CLIENT_EMAIL, name="Demo Client", role=UserRole.CLIENT
            )
            session.add(client)
        if password:
            auditor.password_hash = hash_password(password)
            client.password_hash = hash_password(password)
        session.flush()
        engagement = session.scalar(select(Engagement).where(Engagement.firm_id == firm.id))
        if engagement is None:
            engagement = Engagement(
                firm_id=firm.id,
                auditor_id=auditor.id,
                review_period_start=date(2025, 1, 1),
                review_period_end=date(2025, 12, 31),
                due_date=date(2026, 12, 31),
            )
            session.add(engagement)
            initialize_engagement(engagement)
        session.commit()
        return f"firm={firm.id} engagement={engagement.id} items={len(engagement.items)}"


if __name__ == "__main__":
    print(seed())
