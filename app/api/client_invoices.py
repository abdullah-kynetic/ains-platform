"""The client's invoice list (L2-6h). Read-only, own firm only.

A client sees sent and paid invoices of their own firm for this engagement (or for the firm as a
whole). Drafts and voided invoices, line items, notes and internal events never leave the server.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel
from sqlalchemy import or_, select

from app.database.models import Invoice, UserRole

from .engagements import DB, CurrentUser
from .questionnaire import _get_engagement

router = APIRouter(tags=["client-invoices"])


class PortalInvoiceView(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    id: str
    number: str
    issued: date
    due: date
    amount_cents: int
    status: Literal["sent", "paid", "overdue"]


@router.get(
    "/engagements/{engagement_id}/invoices",
    response_model=list[PortalInvoiceView],
    response_model_by_alias=True,
)
def client_invoices(engagement_id: str, db: DB, user: CurrentUser) -> list[PortalInvoiceView]:
    if user.role != UserRole.CLIENT:
        raise HTTPException(403, "Client access required")
    engagement = _get_engagement(db, user, engagement_id)
    today = datetime.now(UTC).date()
    rows = db.scalars(
        select(Invoice)
        .where(
            Invoice.firm_id == engagement.firm_id,
            Invoice.status.in_(["sent", "paid"]),
            or_(Invoice.engagement_id.is_(None), Invoice.engagement_id == engagement.id),
        )
        .order_by(Invoice.issue_date.desc(), Invoice.number.desc())
    ).all()
    return [
        PortalInvoiceView(
            id=row.id,
            number=f"KIEN-{row.number:04d}",
            issued=row.issue_date,
            due=row.due_date,
            amount_cents=row.total_cents,
            status=(
                "paid"
                if row.status == "paid"
                else "overdue"
                if row.due_date < today and row.amount_paid_cents < row.total_cents
                else "sent"
            ),
        )
        for row in rows
    ]
