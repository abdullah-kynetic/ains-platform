"""Idempotent synthetic demo practice for the live demo: one practice, two firms, four people.

Synthetic data only. Run inside the API image on the demo server (see docs/demo/DEPLOY-DEMO.md):

    python -m app.demo_practice_seed --confirm-synthetic-demo \
        --credentials-file /opt/kien/demo-credentials.txt

What it creates (missing parts only, so it is safe to run twice):
* Practice "Synthetic Demo Practice" with ``allow_auditor_as_signer`` on (decision 2026-11-10).
* Quentin (partner, assigned auditor) and a second reviewer, both example.test addresses.
* Firm "Synthetic Demo Securities" with an engagement assigned to Quentin and one client contact.
* Firm "Synthetic Other Firm" with an engagement assigned to nobody (the isolation proof's real
  second firm).

Passwords are random and written only to the credentials file (mode 600, never overwritten; use
``-`` to send them to stdout for a private redirect) and never logged. Demo accounts have no
authenticator: any old TOTP enrollment on them is switched off on every run (sign-in is email +
password, plus an emailed code only when email delivery is configured). It refuses to run if
the database holds any other firm, so it can never mix synthetic data into real records.
"""

from __future__ import annotations

import argparse
import json
import os
import secrets
import sys
from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.security import hash_password
from app.checklist.catalog import initialize_engagement
from app.database.models import Engagement, Firm, Practice, User, UserRole

PRACTICE_NAME = "Synthetic Demo Practice"
DEMO_FIRMS = {"demo-securities": "Synthetic Demo Securities", "demo-other": "Synthetic Other Firm"}
QUENTIN = ("demo-quentin@example.test", "Synthetic Quentin", "partner")
REVIEWER = ("demo-reviewer@example.test", "Synthetic Reviewer", "reviewer")
CLIENT = ("demo-controller@example.test", "Synthetic Demo Controller")


class RefusedError(RuntimeError):
    pass


def seed(db: Session, *, credentials_file: str) -> dict[str, object]:
    others = [slug for slug in db.scalars(select(Firm.slug)) if slug not in DEMO_FIRMS]
    if others:
        raise RefusedError(
            "Refusing: the database holds firms that are not part of the synthetic demo. "
            "Seed an empty demo database only."
        )
    created: list[str] = []
    passwords: dict[str, str] = {}

    def person(email: str, **fields) -> User:
        user = db.scalar(select(User).where(User.email == email))
        if user is None:
            passwords[email] = secrets.token_urlsafe(18)
            user = User(
                email=email,
                password_hash=hash_password(passwords[email]),
                accepted_at=datetime.now(UTC),
                **fields,
            )
            db.add(user)
            created.append(email)
        user.mfa_enabled, user.mfa_secret, user.mfa_enrollment_expires_at = False, None, None
        return user

    practice = db.scalar(select(Practice).where(Practice.name == PRACTICE_NAME))
    if practice is None:
        practice = Practice(name=PRACTICE_NAME, allow_auditor_as_signer=True)
        db.add(practice)
        db.flush()
        created.append(PRACTICE_NAME)
    quentin = person(
        QUENTIN[0],
        name=QUENTIN[1],
        role=UserRole.AUDITOR,
        practice_id=practice.id,
        team_role=QUENTIN[2],
    )
    person(
        REVIEWER[0],
        name=REVIEWER[1],
        role=UserRole.AUDITOR,
        practice_id=practice.id,
        team_role=REVIEWER[2],
    )
    db.flush()
    for slug, name in DEMO_FIRMS.items():
        firm = db.scalar(select(Firm).where(Firm.slug == slug))
        if firm is None:
            firm = Firm(name=name, slug=slug)
            db.add(firm)
            db.flush()
            created.append(name)
        if db.scalar(select(Engagement.id).where(Engagement.firm_id == firm.id)) is None:
            engagement = Engagement(
                firm_id=firm.id,
                # The second firm stays unassigned: it is the real "another firm" for isolation.
                auditor_id=quentin.id if slug == "demo-securities" else None,
                review_period_start=date(2025, 1, 1),
                review_period_end=date(2025, 12, 31),
            )
            db.add(engagement)
            initialize_engagement(engagement)
            db.flush()
        if slug == "demo-securities":
            person(CLIENT[0], name=CLIENT[1], role=UserRole.CLIENT, firm_id=firm.id)
    db.commit()
    if passwords:
        lines = ["Synthetic demo sign-ins (delete this file after the demo)."]
        lines += [f"{email}  {password}" for email, password in passwords.items()]
        if credentials_file == "-":
            # For a container run: the caller redirects stdout into a private host file.
            sys.stdout.write("\n".join(lines) + "\n")
        else:
            # O_EXCL: never overwrite an earlier file; mode 600 from the start.
            fd = os.open(credentials_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "w") as handle:
                handle.write("\n".join(lines) + "\n")
    return {
        "created": created,
        "passwordsWritten": len(passwords),
        "credentialsFile": credentials_file,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.demo_practice_seed")
    parser.add_argument("--confirm-synthetic-demo", action="store_true", required=True)
    parser.add_argument("--credentials-file", required=True)
    args = parser.parse_args(argv)
    from app.database.session import get_session_factory

    with get_session_factory()() as db:
        summary = seed(db, credentials_file=args.credentials_file)
    # The summary goes to stderr so "--credentials-file -" keeps stdout for the credentials only.
    sys.stderr.write(json.dumps(summary, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
