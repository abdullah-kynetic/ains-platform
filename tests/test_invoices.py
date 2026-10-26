"""Synthetic invoice authorization, financial arithmetic and state-machine integration."""

from datetime import UTC, date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.dependencies import get_current_user
from app.database.models import AuditLog, Base, Engagement, Firm, InvoiceEvent, User, UserRole
from app.database.session import get_db
from app.main import create_app


@pytest.fixture
def invoices():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)
    with factory() as db:
        firms = [Firm(name=f"Synthetic {i}", slug=f"synthetic-{i}") for i in range(4)]
        db.add_all(firms)
        db.flush()
        users = [
            User(
                email=f"synthetic-{i}@example.test",
                name=f"Auditor {i}",
                firm_id=firms[i // 2].id,
                role=UserRole.AUDITOR,
            )
            for i in range(3)
        ]
        users.append(
            User(
                email="client@example.test",
                name="Client",
                role=UserRole.CLIENT,
                firm_id=firms[2].id,
            )
        )
        db.add_all(users)
        db.flush()
        engagements = [
            Engagement(
                firm_id=firms[2].id,
                auditor_id=u.id,
                review_period_start=date(2025, 1, 1),
                review_period_end=date(2025, 12, 31),
            )
            for u in users[:3]
        ]
        db.add_all(engagements)
        db.commit()
        ids = {
            "firms": [f.id for f in firms],
            "users": [u.id for u in users],
            "engagements": [e.id for e in engagements],
        }
    current = [ids["users"][0]]

    def database():
        with factory() as db:
            yield db

    def user():
        with factory() as db:
            return db.get(User, current[0])

    app = create_app()
    app.dependency_overrides[get_db] = database
    app.dependency_overrides[get_current_user] = user
    with TestClient(app) as client:
        yield client, factory, ids, current
    engine.dispose()


def payload(ids, **changes):
    today = datetime.now(UTC).date()
    return {
        "firmId": ids["firms"][2],
        "engagementId": ids["engagements"][0],
        "issueDate": str(today - timedelta(days=30)),
        "dueDate": str(today - timedelta(days=1)),
        "lineItems": [
            {"description": "Synthetic review", "quantity": "1.25", "rateCents": 1002},
            {"description": "Synthetic preparation", "quantity": "2", "rateCents": 500},
        ],
        **changes,
    }


def create(client, ids, **changes):
    response = client.post("/auditor/invoices", json=payload(ids, **changes))
    assert response.status_code == 201, response.text
    return response.json()


def test_crud_totals_filters_and_ledger(invoices):
    client, factory, ids, _ = invoices
    invoice = create(client, ids)
    assert invoice["totalCents"] == invoice["subtotalCents"] == 2253
    assert invoice["lineItems"][0]["amountCents"] == 1253  # half-up, never binary float
    assert invoice["number"] == 1
    assert invoice["overdue"] is False
    path = f"/auditor/invoices/{invoice['id']}"
    changed = client.patch(path, json=payload(ids, notes="Synthetic note")).json()
    assert changed["notes"] == "Synthetic note"
    assert client.get(path).json()["totalCents"] == 2253
    assert len(client.get("/auditor/invoices?status=draft").json()) == 1
    assert client.get("/auditor/invoices?status=overdue").json() == []
    assert client.get("/auditor/invoices?client=another").json() == []
    assert client.get("/auditor/invoices?since=2100-01-01").json() == []
    assert client.get("/auditor/invoices?until=2000-01-01").json() == []
    assert client.get("/auditor/invoices?since=2100-01-01&until=2000-01-01").status_code == 422
    assert client.post(path + "/sent").json()["overdue"] is True
    assert len(client.get("/auditor/invoices?status=overdue").json()) == 1
    assert client.patch(path, json=payload(ids)).status_code == 409
    with factory() as db:
        assert len(db.scalars(select(InvoiceEvent)).all()) == 3
        assert [a.action for a in db.scalars(select(AuditLog)).all()] == [
            "invoice.created",
            "invoice.updated",
            "invoice.sent",
        ]


def test_partial_payments_full_payment_and_history(invoices):
    client, _, ids, _ = invoices
    invoice = create(client, ids)
    path = f"/auditor/invoices/{invoice['id']}"
    paid_date = str(datetime.now(UTC).date())
    payment = {"paidDate": paid_date, "amountCents": 1000}
    assert client.post(path + "/paid", json=payment).status_code == 409
    client.post(path + "/sent")
    partial = client.post(path + "/paid", json=payment).json()
    assert partial["status"] == "sent" and partial["overdue"]
    assert partial["amountPaidCents"] == 1000 and partial["paidAt"] is None
    assert partial["events"][-1]["metadata"] == {"paid_date": paid_date}
    assert client.post(path + "/void").status_code == 409
    assert client.post(path + "/paid", json={**payment, "amountCents": 2000}).status_code == 422
    paid = client.post(path + "/paid", json={**payment, "amountCents": 1253}).json()
    assert paid["status"] == "paid" and not paid["overdue"] and paid["paidAt"] == paid_date
    assert len([e for e in paid["events"] if e["type"] == "payment"]) == 2
    assert client.post(path + "/paid", json=payment).status_code == 409
    assert client.post(path + "/sent").status_code == 409
    assert client.post(path + "/void").status_code == 409


@pytest.mark.parametrize("state", ["draft", "sent"])
def test_void_and_terminal_state(invoices, state):
    client, _, ids, _ = invoices
    invoice = create(client, ids)
    path = f"/auditor/invoices/{invoice['id']}"
    if state == "sent":
        client.post(path + "/sent")
    assert client.post(path + "/void").json()["status"] == "void"
    assert client.post(path + "/sent").status_code == 409
    assert client.post(path + "/void").status_code == 409
    assert client.patch(path, json=payload(ids)).status_code == 409


def test_numbering_shared_firm_and_independent_firms(invoices):
    client, _, ids, current = invoices
    assert create(client, ids)["number"] == 1
    assert create(client, ids)["number"] == 2
    current[0] = ids["users"][1]  # same issuer firm, separate assignment
    assert create(client, ids, engagementId=ids["engagements"][1])["number"] == 3
    current[0] = ids["users"][2]
    assert create(client, ids, engagementId=ids["engagements"][2])["number"] == 1


@pytest.mark.parametrize("who", [2, 3])
def test_every_endpoint_denies_other_auditor_or_client(invoices, who):
    client, _, ids, current = invoices
    invoice = create(client, ids)
    current[0] = ids["users"][who]
    path = f"/auditor/invoices/{invoice['id']}"
    denied = 403 if who == 3 else 404
    for response in [
        client.get(path),
        client.patch(path, json=payload(ids)),
        client.post(path + "/sent"),
        client.post(path + "/void"),
        client.post(path + "/paid", json={"paidDate": str(date.today()), "amountCents": 1}),
    ]:
        assert response.status_code == denied
    listing = client.get("/auditor/invoices")
    assert listing.status_code == (403 if who == 3 else 200)
    if who != 3:
        assert listing.json() == []
    assert client.post("/auditor/invoices", json=payload(ids)).status_code == denied
    assert client.get("/auditor/invoices/options").status_code == (403 if who == 3 else 200)


def test_assignment_removal_and_forged_client_engagement(invoices):
    client, factory, ids, _ = invoices
    assert (
        client.post("/auditor/invoices", json=payload(ids, firmId=ids["firms"][3])).status_code
        == 404
    )
    invoice = create(client, ids)
    with factory() as db:
        db.get(Engagement, ids["engagements"][0]).auditor_id = ids["users"][2]
        db.commit()
    assert client.get(f"/auditor/invoices/{invoice['id']}").status_code == 404
    assert client.get("/auditor/invoices").json() == []


@pytest.mark.parametrize(
    "changes",
    [
        {"lineItems": []},
        {"dueDate": "2000-01-01"},
        {"currency": "JPY"},
        {"lineItems": [{"description": " ", "quantity": "1", "rateCents": 100}]},
        {"lineItems": [{"description": "x", "quantity": "1.001", "rateCents": 100}]},
        {"lineItems": [{"description": "x", "quantity": "1", "rateCents": 1.1}]},
        {"lineItems": [{"description": "x", "quantity": "1", "rateCents": -1}]},
        {"lineItems": [{"description": "x", "quantity": "0", "rateCents": 100}]},
        {"lineItems": [{"description": "x", "quantity": "1", "rateCents": 0}]},
    ],
)
def test_invalid_financial_input(invoices, changes):
    client, _, ids, _ = invoices
    assert client.post("/auditor/invoices", json=payload(ids, **changes)).status_code == 422


def test_optional_engagement_due_today_and_payment_dates(invoices):
    client, _, ids, _ = invoices
    invoice = create(client, ids, engagementId=None, dueDate=str(datetime.now(UTC).date()))
    path = f"/auditor/invoices/{invoice['id']}"
    assert not client.post(path + "/sent").json()["overdue"]
    for when in ["2000-01-01", "2100-01-01"]:
        assert (
            client.post(path + "/paid", json={"paidDate": when, "amountCents": 1}).status_code
            == 422
        )


def test_seed_is_synthetic_only_idempotent_and_preserves_credentials(invoices, monkeypatch):
    from app import invoice_seed
    from app.database.models import Invoice

    _, factory, ids, _ = invoices
    monkeypatch.setattr(invoice_seed, "get_session_factory", lambda: factory)
    with factory() as db:
        user = db.get(User, ids["users"][0])
        user.email = invoice_seed.DEMO_EMAIL
        user.password_hash = "synthetic-unchanged-hash"
        db.commit()
    assert invoice_seed.seed() == 4
    assert invoice_seed.seed() == 0
    with factory() as db:
        assert len(db.scalars(select(Invoice)).all()) == 4
        assert db.get(User, ids["users"][0]).password_hash == "synthetic-unchanged-hash"


def test_whole_issuer_firm_shares_invoice_and_assignment(invoices):
    client, _, ids, current = invoices
    invoice = create(client, ids)
    current[0] = ids["users"][1]
    path = f"/auditor/invoices/{invoice['id']}"
    assert client.get(path).status_code == 200
    assert [i["id"] for i in client.get("/auditor/invoices").json()] == [invoice["id"]]
    assert client.patch(path, json=payload(ids, notes="Shared synthetic draft")).status_code == 200
    assert client.post(path + "/sent").status_code == 200
    response = client.post(
        path + "/paid", json={"paidDate": str(date.today()), "amountCents": 1}
    )
    assert response.status_code == 200
