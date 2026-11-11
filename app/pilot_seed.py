"""Idempotent synthetic pilot workspace: three firms, one practice, one auditor, engagements.

Synthetic names only. It never runs a model and prints no tokens, emails or passwords.

    uv run python -m app.pilot_seed            # create what is missing; sends nothing
    uv run python -m app.pilot_seed --send     # also email each NEW invitation through Resend

Rules:
* Refuses to run when ``ENV=production`` and ``INVITATION_PREVIEW_ENABLED`` is on (the preview
  path returns invitation links in API responses).
* Invitations are created only for the addresses in ``PILOT_INVITEE_EMAILS`` (comma separated,
  matched to the firms in order). Without ``--send`` they are created but not delivered; an
  auditor resends them from the invitations screen, which issues a fresh link.
* An invitation is emailed only when this run creates it. If delivery fails, that invitation is
  rolled back so the next run can try again.
* The auditor gets a password only when ``DEMO_PASSWORD`` is set; sign-in then also uses an
  emailed code when email is configured.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.security import hash_password, new_invitation_token
from app.checklist.catalog import initialize_engagement
from app.config import Settings, get_settings
from app.database.models import (
    AuditLog,
    ClientInvitation,
    Engagement,
    Firm,
    Practice,
    User,
    UserRole,
)
from app.tenancy import require_firm_slug

PILOT_FIRMS = [
    ("pilot-alpha", "Pilot Alpha Securities (synthetic)"),
    ("pilot-beta", "Pilot Beta Capital (synthetic)"),
    ("pilot-gamma", "Pilot Gamma Brokerage (synthetic)"),
]
PRACTICE_NAME = "Synthetic pilot practice"
AUDITOR_EMAIL = "pilot-auditor@example.test"


def parse_invitees(raw: str) -> list[str]:
    return [part.strip().lower() for part in raw.split(",") if part.strip()]


def seed(db: Session, settings: Settings, *, send: bool = False) -> dict[str, Any]:
    if settings.env == "production" and settings.invitation_preview_enabled:
        raise RuntimeError("Refusing to seed: INVITATION_PREVIEW_ENABLED must be off in production")
    summary: dict[str, Any] = {
        "firms": 0,
        "engagements": 0,
        "invitationsCreated": 0,
        "invitationsSent": 0,
        "slugs": [slug for slug, _ in PILOT_FIRMS],
    }
    practice = db.scalar(select(Practice).where(Practice.name == PRACTICE_NAME))
    if practice is None:
        practice = Practice(name=PRACTICE_NAME)
        db.add(practice)
        db.flush()
    password = settings.demo_password.get_secret_value() or None
    auditor = db.scalar(select(User).where(User.email == AUDITOR_EMAIL))
    if auditor is None:
        auditor = User(
            email=AUDITOR_EMAIL,
            name="Pilot Auditor (synthetic)",
            role=UserRole.AUDITOR,
            practice_id=practice.id,
            team_role="partner",
        )
        db.add(auditor)
    if password and not auditor.password_hash:
        auditor.password_hash = hash_password(password)
    db.flush()
    invitees = parse_invitees(settings.pilot_invitee_emails)
    for index, (slug, name) in enumerate(PILOT_FIRMS):
        require_firm_slug(slug)
        firm = db.scalar(select(Firm).where(Firm.slug == slug))
        if firm is None:
            firm = Firm(name=name, slug=slug)
            db.add(firm)
            db.flush()
            summary["firms"] += 1
        engagement = db.scalar(select(Engagement).where(Engagement.firm_id == firm.id))
        if engagement is None:
            engagement = Engagement(
                firm_id=firm.id,
                auditor_id=auditor.id,
                review_period_start=date(2025, 1, 1),
                review_period_end=date(2025, 12, 31),
                due_date=date.today() + timedelta(days=60),
            )
            db.add(engagement)
            initialize_engagement(engagement)
            db.flush()
            summary["engagements"] += 1
        email = invitees[index] if index < len(invitees) else None
        if email is None:
            continue
        exists = db.scalar(select(ClientInvitation.id).where(ClientInvitation.email == email))
        if exists or db.scalar(select(User.id).where(User.email == email)):
            continue
        token, token_hash = new_invitation_token()
        expires = datetime.now(UTC) + timedelta(hours=settings.client_invitation_ttl_hours)
        invitation = ClientInvitation(
            firm_id=firm.id,
            engagement_id=engagement.id,
            email=email,
            name=f"{name} contact",
            token_hash=token_hash,
            expires_at=expires,
            created_by_id=auditor.id,
        )
        db.add(invitation)
        db.flush()
        db.add(
            AuditLog(
                firm_id=firm.id,
                actor_id=auditor.id,
                action="client_invitation.created",
                entity_type="client_invitation",
                entity_id=invitation.id,
                details={"email": email, "engagement_id": engagement.id, "source": "pilot_seed"},
            )
        )
        if send:
            from app.auth.email import ResendSender

            try:
                ResendSender(settings, "invitation").send(
                    email=email, token=token, expires_at=expires, slug=slug
                )
            except Exception:
                db.rollback()
                raise
            summary["invitationsSent"] += 1
        summary["invitationsCreated"] += 1
        db.commit()
    db.commit()
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.pilot_seed")
    parser.add_argument("--send", action="store_true", help="email each newly created invitation")
    args = parser.parse_args(argv)
    from app.database.session import get_session_factory

    with get_session_factory()() as db:
        summary = seed(db, get_settings(), send=args.send)
    sys.stdout.write(json.dumps(summary, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
