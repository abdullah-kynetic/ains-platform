"""Synthetic workflow fixtures for the e2e-live specs (Lane 2 owns this file).

Adds one extra firm, ``kynetic-flow`` (browse it at http://kynetic-flow.localhost:3100), in four
known states so each spec starts where it needs to. It uses its own auditor, reviewer, partner
and client so the original e2e firm (one engagement for ``e2e-auditor``) is untouched.
SYNTHETIC data and test-only passwords. Idempotent. Refuses a Postgres DATABASE_URL.

    from scripts.e2e_seed import seed_workflow_fixtures
    seed_workflow_fixtures(session)            # or: uv run python -m scripts.e2e_seed

Engagements (period year in brackets):
  testing   (2021)  nothing concluded yet; one receipt-only document; no findings
  ready     (2022)  every item concluded, workpaper reviewed, independence cleared, one released
                    finding already answered by the client: reviewer approval can start now
  signed    (2023)  reviewer approved, partner signed, completed; client has not confirmed
  confirmed (2024)  as signed, client confirmed, one sent invoice
"""

from __future__ import annotations

import hashlib
import os
import sys
from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from scripts.e2e_backend import AUDITOR_PASSWORD, CLIENT_PASSWORD

FIRM_SLUG = "kynetic-flow"
USERS = {
    "auditor": "flow-auditor@example.test",
    "reviewer": "flow-reviewer@example.test",
    "partner": "flow-partner@example.test",
    "client": "flow-client@example.test",
}
YEARS = {"testing": 2021, "ready": 2022, "signed": 2023, "confirmed": 2024}


def _fingerprint(sections: list[dict[str, str]]) -> str:
    text = "\n\n".join(f"{s['title']}\n{s['body']}" for s in sections)
    return hashlib.sha256(text.encode()).hexdigest()


def seed_workflow_fixtures(db: Session) -> dict[str, Any]:
    from app.auth.security import hash_password
    from app.checklist.catalog import initialize_engagement
    from app.database.models import (
        Document,
        Engagement,
        EngagementSignoff,
        EngagementStatus,
        Finding,
        Firm,
        Practice,
        ResponseRequest,
        SampleItem,
        SampleSet,
        User,
        UserRole,
        Workpaper,
    )
    from app.invoicing import InvoiceInput, LineInput, create_invoice, record

    firm = db.scalar(select(Firm).where(Firm.slug == FIRM_SLUG))
    if firm is not None:
        ids = {
            name: db.scalar(
                select(Engagement.id).where(
                    Engagement.firm_id == firm.id,
                    Engagement.review_period_start == date(year, 1, 1),
                )
            )
            for name, year in YEARS.items()
        }
        return {"firm": firm.id, "engagements": ids, "created": False}
    now = datetime.now(UTC)
    firm = Firm(name="Synthetic Flow Securities", slug=FIRM_SLUG)
    practice = Practice(name="Synthetic Flow Practice")
    db.add_all([firm, practice])
    db.flush()

    def person(key: str, role: UserRole, password: str, **extra: Any) -> User:
        user = User(
            email=USERS[key],
            name=f"Synthetic Flow {key.title()}",
            role=role,
            password_hash=hash_password(password),
            accepted_at=now,
            **extra,
        )
        db.add(user)
        return user

    auditor = person("auditor", UserRole.AUDITOR, AUDITOR_PASSWORD, practice_id=practice.id)
    reviewer = person(
        "reviewer",
        UserRole.AUDITOR,
        AUDITOR_PASSWORD,
        practice_id=practice.id,
        team_role="reviewer",
    )
    partner = person(
        "partner", UserRole.AUDITOR, AUDITOR_PASSWORD, practice_id=practice.id, team_role="partner"
    )
    auditor.team_role = "auditor"
    client = person("client", UserRole.CLIENT, CLIENT_PASSWORD, firm_id=firm.id)
    db.flush()

    engagements: dict[str, Engagement] = {}
    for name, year in YEARS.items():
        e = Engagement(
            firm_id=firm.id,
            auditor_id=auditor.id,
            review_period_start=date(year, 1, 1),
            review_period_end=date(year, 12, 31),
            due_date=date.today() + timedelta(days=30),
        )
        db.add(e)
        db.flush()
        initialize_engagement(e)
        db.flush()
        engagements[name] = e
        item = next(i for i in e.items if i.item_key == "AML-BD-001")
        db.add(
            Document(
                firm_id=firm.id,
                engagement_id=e.id,
                item_instance_id=item.id,
                uploaded_by_id=client.id,
                original_name="synthetic-flow-policy.pdf",
                content_type="application/pdf",
                size_bytes=28,
                egnyte_path=f"/synthetic-flow/receipt-only/{year}/policy.pdf",
                sha256=hashlib.sha256(f"flow-{year}".encode()).hexdigest(),
                number="1.1",
            )
        )
        e.document_seq = 1

    for name in ("ready", "signed", "confirmed"):
        e = engagements[name]
        for item in e.items:
            item.conclusion = "pass"
            item.conclusion_updated_at, item.conclusion_updated_by_id = now, auditor.id
        db.add(
            Workpaper(
                firm_id=firm.id,
                engagement_id=e.id,
                request_id="AML-BD-001",
                procedure="Read the written AML program (synthetic).",
                evidence_ids=[],
                conclusion="pass",
                preparer_id=auditor.id,
                reviewer_id=reviewer.id,
                reviewed_at=now,
            )
        )
        sample = SampleSet(
            firm_id=firm.id,
            engagement_id=e.id,
            area="Transaction monitoring alerts",
            population=100,
            sample_size=2,
            method="Random",
            created_by_id=auditor.id,
        )
        db.add(sample)
        db.flush()
        for position, reference in enumerate(("ITEM-001", "ITEM-002")):
            db.add(
                SampleItem(
                    firm_id=firm.id,
                    set_id=sample.id,
                    position=position,
                    reference=reference,
                    result="pass",
                    updated_by_id=auditor.id,
                )
            )
        finding = Finding(
            firm_id=firm.id,
            engagement_id=e.id,
            title="Alert closures lack a written reason (synthetic)",
            rule="FINRA Rule 3310(a) (synthetic text)",
            condition="Some alerts were closed without a recorded reason.",
            cause="No closure template.",
            effect="Reviews cannot be reconstructed.",
            recommendation="Require a reason on every closure.",
            severity="moderate",
            citations=[{"document": "synthetic-flow-policy.pdf", "page": 1}],
            status="responded",
            management_response="We will add a closure template.",
            responded_at=now,
            created_by_id=auditor.id,
        )
        db.add(finding)
        db.flush()
        db.add(
            ResponseRequest(
                firm_id=firm.id,
                engagement_id=e.id,
                finding_id=finding.id,
                title="Alert-closure documentation",
                request_text="Please describe how closures are documented.",
                status="responded",
                response="We will add a closure template.",
                responded_at=now,
                responded_by_id=client.id,
                released_by_id=auditor.id,
            )
        )
        answers = [{"id": f"q{i}", "answer": "no"} for i in range(1, 6)]
        signoff = EngagementSignoff(
            firm_id=firm.id,
            engagement_id=e.id,
            independence_answers=answers,
            independence_conclusion="independent",
            declared_by_id=auditor.id,
            declared_at=now,
        )
        db.add(signoff)
        if name == "ready":
            continue
        sections = [
            {"id": "scope", "title": "Scope and objective", "body": "Synthetic scope."},
            {"id": "results", "title": "Summary of results", "body": "Pass: 34."},
            {"id": "finding-1", "title": "Finding 1", "body": "Synthetic finding text."},
            {"id": "limitations", "title": "Limitations", "body": "Synthetic limitations."},
        ]
        signoff.reviewer_id, signoff.reviewer_approved_at = reviewer.id, now
        signoff.reviewer_note = "Reviewed (synthetic)."
        signoff.partner_id, signoff.partner_signed_at = partner.id, now
        signoff.signed_sections = sections
        signoff.partner_fingerprint = _fingerprint(sections)
        signoff.completed_at = now
        e.status = EngagementStatus.COMPLETE
        if name == "confirmed":
            e.report_confirmed_at = now
            e.report_confirmed_by_id = client.id
            e.report_confirmed_sha256 = signoff.partner_fingerprint
    db.flush()
    confirmed = engagements["confirmed"]
    invoice = create_invoice(
        db,
        auditor,
        InvoiceInput(
            firm_id=firm.id,
            engagement_id=confirmed.id,
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            line_items=[LineInput(description="Synthetic review", quantity="1", rate_cents=125000)],
        ),
    )
    invoice.engagement_id = confirmed.id
    before, invoice.status = invoice.status, "sent"
    record(db, invoice, auditor, "sent", before)
    db.commit()
    return {
        "firm": firm.id,
        "engagements": {name: e.id for name, e in engagements.items()},
        "created": True,
    }


def main() -> int:
    if "postgres" in os.environ.get("DATABASE_URL", ""):
        sys.exit("Refusing to run: DATABASE_URL points at Postgres. This script is synthetic-only.")
    from app.database.session import get_session_factory

    with get_session_factory()() as db:
        result = seed_workflow_fixtures(db)
    sys.stdout.write(f"{result}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
