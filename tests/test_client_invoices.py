"""L2-6h: the client's read-only invoice list, and overdue-invoice notifications."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.database.models import Invoice, InvoiceIssuer, InvoiceLineItem
from tests.test_backend_api import backend, sign_in_auditor, sign_in_client  # noqa: F401


def _invoice(
    db,
    issuer,
    ids,
    number,
    status,
    *,
    firm="firm_a",
    due_days=10,
    paid=0,
    engagement="engagement_a",
    notes="",
):
    today = datetime.now(UTC).date()
    invoice = Invoice(
        issuer_id=issuer.id,
        firm_id=ids[firm],
        engagement_id=ids[engagement] if engagement else None,
        auditor_id=ids["auditor"],
        number=number,
        status=status,
        issue_date=today - timedelta(days=30),
        due_date=today + timedelta(days=due_days),
        notes=notes,
        subtotal_cents=125000,
        total_cents=125000,
        amount_paid_cents=paid,
    )
    invoice.line_items = [
        InvoiceLineItem(
            description="INTERNAL LINE",
            quantity=1,
            rate_cents=125000,
            amount_cents=125000,
            position=0,
        )
    ]
    db.add(invoice)
    return invoice


def _seed(factory, ids):
    with factory() as db:
        issuer = InvoiceIssuer(id="issuer-synthetic", auditor_id=ids["auditor"], next_number=10)
        db.add(issuer)
        db.flush()
        _invoice(db, issuer, ids, 1, "sent", due_days=10)
        _invoice(db, issuer, ids, 2, "sent", due_days=-3)
        _invoice(db, issuer, ids, 3, "paid", due_days=-30, paid=125000)
        _invoice(db, issuer, ids, 4, "draft")
        _invoice(db, issuer, ids, 5, "void")
        _invoice(db, issuer, ids, 6, "sent", engagement=None, notes="PRIVATE NOTE")
        _invoice(db, issuer, ids, 7, "sent", firm="firm_b", engagement="engagement_b")
        db.commit()


def test_client_sees_only_own_sent_and_paid_invoices_with_allowed_fields(backend):  # noqa: F811
    client, factory, ids, *_ = backend
    _seed(factory, ids)
    sign_in_client(client)
    response = client.get(f"/engagements/{ids['engagement_a']}/invoices")
    assert response.status_code == 200
    rows = response.json()
    assert {r["number"]: r["status"] for r in rows} == {
        "KIEN-0001": "sent",
        "KIEN-0002": "overdue",
        "KIEN-0003": "paid",
        "KIEN-0006": "sent",
    }
    assert set(rows[0]) == {"id", "number", "issued", "due", "amountCents", "status"}
    assert rows[0]["amountCents"] == 125000
    for hidden in ("INTERNAL LINE", "PRIVATE NOTE", "KIEN-0004", "KIEN-0005", "KIEN-0007"):
        assert hidden not in response.text
    # A foreign engagement is denied, and an auditor cannot use the client route.
    assert client.get(f"/engagements/{ids['engagement_b']}/invoices").status_code == 404
    sign_in_auditor(client)
    assert client.get(f"/engagements/{ids['engagement_a']}/invoices").status_code == 403


def test_overdue_invoice_becomes_an_auditor_notification(backend):  # noqa: F811
    client, factory, ids, *_ = backend
    _seed(factory, ids)
    sign_in_auditor(client)
    items = [n for n in client.get("/auditor/notifications").json() if n["kind"] == "invoice"]
    assert [n["title"] for n in items] == ["Invoice KIEN-0002 is overdue"]
    assert items[0]["href"].startswith("/auditor/invoices/")
    with factory() as db:
        invoice = db.scalar(select(Invoice).where(Invoice.number == 2))
        invoice.status, invoice.amount_paid_cents = "paid", invoice.total_cents
        db.commit()
    assert not [n for n in client.get("/auditor/notifications").json() if n["kind"] == "invoice"]
