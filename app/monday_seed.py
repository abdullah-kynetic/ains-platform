"""Enable shared billing for the exact synthetic demo, preserving its existing invoices.

No credentials are created or changed. Ordinary firms/users/invoices are never modified.
"""

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select

from app.database.models import AuditLog, Engagement, Firm, Invoice, InvoiceIssuer, User, UserRole
from app.database.session import get_session_factory
from app.invoicing import InvoiceInput, LineInput, create_invoice

DEMO_EMAIL = "demo-auditor@kiensolutions.com"
COLLEAGUE_EMAIL = "monday-billing-colleague@example.test"
MARKER = "Synthetic firm-sharing demonstration · monday-v1"


def seed() -> str:
    with get_session_factory()() as db:
        user = db.scalar(select(User).where(User.email == DEMO_EMAIL).with_for_update())
        if not user or user.role != UserRole.AUDITOR:
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
        if not user.firm_id:
            firm = db.scalar(select(Firm).where(Firm.slug == "monday-demo-audit-synthetic"))
            if not firm:
                firm = Firm(name="Demo Audit Firm (synthetic)", slug="monday-demo-audit-synthetic")
                db.add(firm)
                db.flush()
            user.firm_id = firm.id
            db.flush()
        else:
            firm = db.get(Firm, user.firm_id)
            if "synthetic" not in (firm.name + firm.slug).lower():
                raise RuntimeError("Demo issuer firm must be explicitly synthetic")
        issuer = db.get(InvoiceIssuer, firm.id)
        if not issuer:
            issuer = InvoiceIssuer(id=firm.id, firm_id=firm.id, next_number=1)
            db.add(issuer)
            db.flush()
        legacy = db.get(InvoiceIssuer, user.id)
        moved = 0
        if legacy and legacy.auditor_id == user.id:
            rows = db.scalars(
                select(Invoice).where(
                    Invoice.issuer_id == legacy.id,
                    Invoice.auditor_id == user.id,
                )
            ).all()
            if rows and db.scalar(
                select(Invoice.id).where(Invoice.issuer_id == issuer.id).limit(1)
            ):
                raise RuntimeError("Refuse to combine two populated synthetic invoice ledgers")
            for invoice in rows:
                if "synthetic" not in (invoice.firm.name + invoice.firm.slug).lower():
                    raise RuntimeError("Refuse to move a non-synthetic billed client")
                invoice.issuer_id = issuer.id
                moved += 1
            issuer.next_number = max(issuer.next_number, legacy.next_number)
            db.flush()
        largest = db.scalar(select(func.max(Invoice.number)).where(Invoice.issuer_id == issuer.id))
        issuer.next_number = max(issuer.next_number, (largest or 0) + 1)
        colleague = db.scalar(select(User).where(User.email == COLLEAGUE_EMAIL))
        if not colleague:
            colleague = User(
                firm_id=firm.id,
                email=COLLEAGUE_EMAIL,
                name="Synthetic billing colleague",
                role=UserRole.AUDITOR,
            )
            db.add(colleague)
            db.flush()
        elif colleague.firm_id != firm.id or colleague.role != UserRole.AUDITOR:
            raise RuntimeError("Synthetic colleague scope mismatch")
        invoice = db.scalar(
            select(Invoice).where(Invoice.issuer_id == issuer.id, Invoice.notes == MARKER)
        )
        if not invoice:
            today = datetime.now(UTC).date()
            invoice = create_invoice(
                db,
                colleague,
                InvoiceInput(
                    firm_id=engagement.firm_id,
                    engagement_id=engagement.id,
                    issue_date=today,
                    due_date=today + timedelta(days=14),
                    notes=MARKER,
                    line_items=[
                        LineInput(
                            description="Synthetic shared-firm review",
                            quantity="1",
                            rate_cents=12500,
                        )
                    ],
                ),
            )
        if moved:
            db.add(
                AuditLog(
                    firm_id=firm.id,
                    actor_id=user.id,
                    action="invoice.demo_firm_scope_enabled",
                    entity_type="user",
                    entity_id=user.id,
                    details={"synthetic": True, "invoices": moved},
                )
            )
        db.commit()
        return invoice.id


if __name__ == "__main__":
    print(f"Synthetic colleague-created invoice: {seed()}")
