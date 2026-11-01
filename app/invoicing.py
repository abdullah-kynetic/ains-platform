"""Auditor invoice rules. All amounts are integer minor units (two decimal currencies)."""

from datetime import UTC, date, datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Literal

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel
from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.database.models import (
    AuditLog,
    Engagement,
    Firm,
    Invoice,
    InvoiceEvent,
    InvoiceIssuer,
    InvoiceLineItem,
    User,
)

InvoiceStatus = Literal["draft", "sent", "paid", "void"]
# Only currencies whose minor unit is 1/100. No conversion or tax calculation in v1.
Currency = Literal["USD", "EUR", "GBP", "CAD", "AUD", "CHF"]


class InvoiceModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)


class LineInput(InvoiceModel):
    description: str = Field(min_length=1, max_length=1000)
    quantity: Decimal = Field(gt=0, le=1000000, max_digits=12, decimal_places=2)
    rate_cents: int = Field(ge=0, le=100000000, strict=True)

    @model_validator(mode="after")
    def clean(self):
        self.description = self.description.strip()
        if not self.description:
            raise ValueError("Line description is required")
        return self

    def amount(self) -> int:
        return int((self.quantity * self.rate_cents).quantize(Decimal(1), rounding=ROUND_HALF_UP))


class InvoiceInput(InvoiceModel):
    firm_id: str
    engagement_id: str | None = None
    issue_date: date
    due_date: date
    currency: Currency = "USD"
    notes: str = Field(default="", max_length=5000)
    line_items: list[LineInput] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def valid(self):
        if self.due_date < self.issue_date:
            raise ValueError("Due date must be on or after issue date")
        total = sum(line.amount() for line in self.line_items)
        if not 0 < total <= 100000000000:
            raise ValueError("Invoice total must be positive and at most 1,000,000,000.00")
        return self


class PaymentInput(InvoiceModel):
    paid_date: date
    amount_cents: int = Field(gt=0, le=100000000000, strict=True)

    @model_validator(mode="after")
    def valid(self):
        if self.paid_date > datetime.now(UTC).date():
            raise ValueError("Payment date cannot be in the future")
        return self


def issuer_key(user: User) -> str:
    return user.firm_id or user.id


def assignment_owner(user: User):
    """Billing is shared by the issuer firm; legacy unbound auditors stay private."""
    if user.firm_id:
        return Engagement.auditor_id.in_(
            select(User.id).where(User.firm_id == user.firm_id, User.role == "auditor")
        )
    return Engagement.auditor_id == user.id


def assigned(db: Session, user: User, firm_id: str, engagement_id: str | None) -> None:
    query = select(Engagement.id).where(
        Engagement.firm_id == firm_id, assignment_owner(user)
    )
    if engagement_id:
        query = query.where(Engagement.id == engagement_id)
    if not db.scalar(query.limit(1)):
        raise HTTPException(404, "Assigned client or engagement not found")


def visible(user: User) -> Select[tuple[Invoice]]:
    assigned_client = (
        select(Engagement.id)
        .where(
            assignment_owner(user),
            Engagement.firm_id == Invoice.firm_id,
            (Invoice.engagement_id.is_(None) | (Engagement.id == Invoice.engagement_id)),
        )
        .exists()
    )
    return select(Invoice).where(Invoice.issuer_id == issuer_key(user), assigned_client)


def record(
    db: Session,
    invoice: Invoice,
    user: User,
    kind: str,
    before: str | None,
    amount: int | None = None,
    details: dict[str, object] | None = None,
) -> None:
    db.add(
        InvoiceEvent(
            invoice_id=invoice.id,
            type=kind,
            from_status=before,
            to_status=invoice.status,
            amount_cents=amount,
            actor_id=user.id,
            details=details or {},
        )
    )
    # Issuer ledger: clients cannot reach invoice data through their firm activity APIs.
    db.add(
        AuditLog(
            firm_id=user.firm_id,
            actor_id=user.id,
            action=f"invoice.{kind}",
            entity_type="invoice",
            entity_id=invoice.id,
            details={
                "from_status": before,
                "to_status": invoice.status,
                "amount_cents": amount,
                **(details or {}),
            },
        )
    )


def apply_input(db: Session, invoice: Invoice, payload: InvoiceInput) -> None:
    for field in ("firm_id", "engagement_id", "issue_date", "due_date", "notes", "currency"):
        setattr(invoice, field, getattr(payload, field))
    # Flush removed positions before replacing lines (unique invoice/position).
    invoice.line_items.clear()
    db.flush()
    invoice.line_items = [
        InvoiceLineItem(
            description=line.description,
            quantity=line.quantity,
            rate_cents=line.rate_cents,
            amount_cents=line.amount(),
            position=position,
        )
        for position, line in enumerate(payload.line_items)
    ]
    invoice.subtotal_cents = invoice.total_cents = sum(line.amount() for line in payload.line_items)


def create_invoice(db: Session, user: User, payload: InvoiceInput) -> Invoice:
    assigned(db, user, payload.firm_id, payload.engagement_id)
    # Lock an existing owner row before creating/locking its counter, including first use.
    if user.firm_id:
        db.scalar(select(Firm).where(Firm.id == user.firm_id).with_for_update())
    else:
        db.scalar(select(User).where(User.id == user.id).with_for_update())
    issuer = db.get(InvoiceIssuer, issuer_key(user))
    if issuer is None:
        issuer = InvoiceIssuer(
            id=issuer_key(user),
            firm_id=user.firm_id,
            auditor_id=None if user.firm_id else user.id,
            next_number=1,
        )
        db.add(issuer)
        db.flush()
    invoice = Invoice(
        issuer_id=issuer.id,
        auditor_id=user.id,
        number=issuer.next_number,
        firm_id=payload.firm_id,
        issue_date=payload.issue_date,
        due_date=payload.due_date,
        subtotal_cents=sum(line.amount() for line in payload.line_items),
        total_cents=sum(line.amount() for line in payload.line_items),
    )
    issuer.next_number += 1
    db.add(invoice)
    db.flush()
    apply_input(db, invoice, payload)
    record(db, invoice, user, "created", None)
    return invoice


def transition(
    db: Session,
    invoice: Invoice,
    user: User,
    action: Literal["sent", "paid", "void"],
    payment: PaymentInput | None = None,
) -> None:
    before = invoice.status
    if action == "sent":
        if before != "draft":
            raise HTTPException(409, "Only a draft can be marked sent")
        invoice.status = "sent"
    elif action == "paid":
        if before != "sent" or payment is None:
            raise HTTPException(409, "Only a sent invoice can receive a payment")
        if payment.paid_date < invoice.issue_date:
            raise HTTPException(422, "Payment date must be on or after issue date")
        if payment.amount_cents > invoice.total_cents - invoice.amount_paid_cents:
            raise HTTPException(422, "Payment exceeds the remaining balance")
        invoice.amount_paid_cents += payment.amount_cents
        if invoice.amount_paid_cents == invoice.total_cents:
            invoice.status = "paid"
            invoice.paid_at = payment.paid_date
    elif action == "void":
        if before not in {"draft", "sent"} or invoice.amount_paid_cents:
            raise HTTPException(409, "Only an unpaid draft or sent invoice can be voided")
        invoice.status = "void"
    record(
        db,
        invoice,
        user,
        "payment" if payment else action,
        before,
        payment.amount_cents if payment else None,
        {"paid_date": payment.paid_date.isoformat()} if payment else None,
    )
