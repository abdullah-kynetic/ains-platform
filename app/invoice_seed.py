"""Idempotent invoice-only synthetic demo seed. Does not create users or alter credentials.

Run ``python -m app.invoice_seed``. Only the named demo auditor's explicitly synthetic
assigned client firms are eligible; other records are never seeded or changed.
"""

from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.database.models import Engagement, Firm, Invoice, User, UserRole
from app.database.session import get_session_factory
from app.invoicing import InvoiceInput, LineInput, PaymentInput, create_invoice, transition

DEMO_EMAIL = "demo-auditor@kiensolutions.com"


def seed() -> int:
    with get_session_factory()() as db:
        auditor = db.scalar(
            select(User).where(User.email == DEMO_EMAIL, User.role == UserRole.AUDITOR)
        )
        if not auditor:
            raise RuntimeError("Existing synthetic demo auditor required")
        engagements = db.scalars(
            select(Engagement)
            .join(Firm)
            .where(
                Engagement.auditor_id == auditor.id,
                (Firm.name.ilike("%synthetic%") | Firm.slug.ilike("%synthetic%")),
            )
            .order_by(Engagement.id)
        ).all()
        if not engagements:
            raise RuntimeError("No explicitly synthetic assigned client firm; seed refused")
        today = datetime.now(UTC).date()
        count = 0
        for index, state in enumerate(("draft", "sent", "overdue", "paid")):
            marker = f"Synthetic demo invoice · invoicing-v1-{state}"
            if db.scalar(
                select(Invoice.id).where(Invoice.auditor_id == auditor.id, Invoice.notes == marker)
            ):
                continue
            engagement = engagements[index % len(engagements)]
            invoice = create_invoice(
                db,
                auditor,
                InvoiceInput(
                    firm_id=engagement.firm_id,
                    engagement_id=engagement.id,
                    issue_date=today - timedelta(days=30),
                    due_date=today + timedelta(days=-7 if state == "overdue" else 14),
                    notes=marker,
                    line_items=[
                        LineInput(
                            description="Independent AML testing (synthetic)",
                            quantity="1",
                            rate_cents=250000 + index * 25000,
                        )
                    ],
                ),
            )
            if state != "draft":
                transition(db, invoice, auditor, "sent")
            if state == "paid":
                transition(
                    db,
                    invoice,
                    auditor,
                    "paid",
                    PaymentInput(
                        paid_date=today,
                        amount_cents=invoice.total_cents,
                    ),
                )
            count += 1
        db.commit()
        return count


if __name__ == "__main__":
    print(f"Created {seed()} synthetic invoices")
