"""Auditor-only, issuer-scoped and assignment-scoped invoicing endpoints."""

from datetime import UTC, date, datetime
from typing import Literal

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.auditor import DB, CurrentUser, _require_auditor
from app.database.models import Engagement, Firm, Invoice, User
from app.invoicing import (
    InvoiceInput,
    PaymentInput,
    apply_input,
    assigned,
    create_invoice,
    record,
    transition,
    visible,
)

router = APIRouter(prefix="/auditor/invoices", tags=["invoices"])


def view(invoice: Invoice) -> dict[str, object]:
    overdue = (
        invoice.status == "sent"
        and invoice.due_date < datetime.now(UTC).date()
        and invoice.amount_paid_cents < invoice.total_cents
    )
    return {
        "id": invoice.id,
        "firmId": invoice.firm_id,
        "firmName": invoice.firm.name,
        "engagementId": invoice.engagement_id,
        "number": invoice.number,
        "status": invoice.status,
        "overdue": overdue,
        "issueDate": invoice.issue_date,
        "dueDate": invoice.due_date,
        "currency": invoice.currency,
        "notes": invoice.notes,
        "subtotalCents": invoice.subtotal_cents,
        "totalCents": invoice.total_cents,
        "amountPaidCents": invoice.amount_paid_cents,
        "paidAt": invoice.paid_at,
        "createdAt": invoice.created_at,
        "updatedAt": invoice.updated_at,
        "lineItems": [
            {
                "id": line.id,
                "description": line.description,
                "quantity": str(line.quantity),
                "rateCents": line.rate_cents,
                "amountCents": line.amount_cents,
                "position": line.position,
            }
            for line in invoice.line_items
        ],
        "events": [
            {
                "id": e.id,
                "type": e.type,
                "fromStatus": e.from_status,
                "toStatus": e.to_status,
                "amountCents": e.amount_cents,
                "occurredAt": e.occurred_at,
                "actorId": e.actor_id,
                "metadata": e.details,
            }
            for e in invoice.events
        ],
    }


def load(invoice_id: str, user: User, db: Session, *, lock: bool = False) -> Invoice:
    _require_auditor(user)
    query = visible(user).where(Invoice.id == invoice_id)
    if lock:
        query = query.with_for_update()
    invoice = db.scalar(query)
    if invoice is None:
        raise HTTPException(404, "Invoice not found")
    return invoice


@router.get("/options")
def options(user: CurrentUser, db: DB):
    _require_auditor(user)
    rows = db.execute(
        select(Engagement, Firm)
        .join(Firm)
        .where(Engagement.auditor_id == user.id)
        .order_by(Firm.name)
    ).all()
    return [
        {
            "id": e.id,
            "firmId": f.id,
            "firmName": f.name,
            "label": f"{e.review_period_start} – {e.review_period_end}",
        }
        for e, f in rows
    ]


@router.get("")
def list_invoices(
    user: CurrentUser,
    db: DB,
    status: Literal["draft", "sent", "paid", "void", "overdue"] | None = None,
    client: str | None = None,
    since: date | None = None,
    until: date | None = None,
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    _require_auditor(user)
    if since and until and since > until:
        raise HTTPException(422, "Start date must be on or before end date")
    query = visible(user).options(
        selectinload(Invoice.firm), selectinload(Invoice.line_items), selectinload(Invoice.events)
    )
    if status == "overdue":
        query = query.where(
            Invoice.status == "sent",
            Invoice.due_date < datetime.now(UTC).date(),
            Invoice.amount_paid_cents < Invoice.total_cents,
        )
    elif status:
        query = query.where(Invoice.status == status)
    if client:
        query = query.where(Invoice.firm_id == client)
    if since:
        query = query.where(Invoice.issue_date >= since)
    if until:
        query = query.where(Invoice.issue_date <= until)
    return [
        view(i)
        for i in db.scalars(query.order_by(Invoice.number.desc()).offset(offset).limit(limit))
    ]


@router.post("", status_code=201)
def create(payload: InvoiceInput, user: CurrentUser, db: DB):
    _require_auditor(user)
    invoice = create_invoice(db, user, payload)
    db.commit()
    return view(invoice)


@router.get("/{invoice_id}")
def get(invoice_id: str, user: CurrentUser, db: DB):
    return view(load(invoice_id, user, db))


@router.patch("/{invoice_id}")
def update(invoice_id: str, payload: InvoiceInput, user: CurrentUser, db: DB):
    invoice = load(invoice_id, user, db, lock=True)
    if invoice.status != "draft":
        raise HTTPException(409, "Only drafts are editable")
    assigned(db, user, payload.firm_id, payload.engagement_id)
    apply_input(db, invoice, payload)
    record(db, invoice, user, "updated", "draft")
    db.commit()
    return view(invoice)


@router.post("/{invoice_id}/sent")
def sent(invoice_id: str, user: CurrentUser, db: DB):
    invoice = load(invoice_id, user, db, lock=True)
    transition(db, invoice, user, "sent")
    db.commit()
    return view(invoice)


@router.post("/{invoice_id}/paid")
def paid(invoice_id: str, payload: PaymentInput, user: CurrentUser, db: DB):
    invoice = load(invoice_id, user, db, lock=True)
    transition(db, invoice, user, "paid", payload)
    db.commit()
    return view(invoice)


@router.post("/{invoice_id}/void")
def void(invoice_id: str, user: CurrentUser, db: DB):
    invoice = load(invoice_id, user, db, lock=True)
    transition(db, invoice, user, "void")
    db.commit()
    return view(invoice)
