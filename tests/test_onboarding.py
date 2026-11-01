"""Authenticated per-user walkthrough persistence and demo-only reset."""

from sqlalchemy import select

from app.database.models import AuditLog, User
from tests.test_backend_api import backend as backend
from tests.test_backend_api import sign_in_auditor, sign_in_client
from tests.test_invoices import invoices as invoices


def test_onboarding_requires_session_and_skip_persists_independently(backend):
    client, factory, ids, _, _ = backend
    assert client.get("/auth/onboarding").status_code == 401
    assert client.post("/auth/onboarding", json={"action": "skipped"}).status_code == 401
    sign_in_client(client)
    assert client.get("/auth/onboarding").json() == {"state": "pending", "flow": "client"}
    assert client.post("/auth/onboarding", json={"action": "skipped"}).json()["state"] == "skipped"
    assert (
        client.post("/auth/onboarding", json={"action": "completed"}).json()["state"] == "skipped"
    )
    client.cookies.clear()
    sign_in_client(client)
    assert client.get("/auth/onboarding").json()["state"] == "skipped"
    client.cookies.clear()
    sign_in_client(client, "beta-client@example.test")
    assert client.get("/auth/onboarding").json()["state"] == "pending"
    assert client.post("/auth/onboarding", json={"action": "reset"}).status_code == 422
    with factory() as db:
        assert db.get(User, ids["client_b"]).onboarding_state is None
        events = db.scalars(select(AuditLog).where(AuditLog.action == "onboarding.skipped")).all()
        assert len(events) == 1 and events[0].actor_id == ids["client_a"]


def test_auditor_completion_persists_and_demo_reset_is_exactly_scoped(backend, monkeypatch):
    from app import onboarding_seed

    client, factory, ids, _, _ = backend
    sign_in_auditor(client)
    assert client.get("/auth/onboarding").json() == {"state": "pending", "flow": "auditor"}
    assert client.post("/auth/onboarding", json={"action": "completed"}).status_code == 200
    assert client.get("/auth/onboarding").json()["state"] == "completed"
    monkeypatch.setattr(onboarding_seed, "get_session_factory", lambda: factory)
    with factory() as db:
        client_user = db.get(User, ids["client_a"])
        client_user.email = onboarding_seed.DEMO_EMAILS[0]
        client_user.onboarding_state = "skipped"
        db.commit()
    assert onboarding_seed.reset() == 1
    with factory() as db:
        assert db.get(User, ids["client_a"]).onboarding_state is None
        assert db.get(User, ids["auditor"]).onboarding_state == "completed"


def test_shared_billing_seed_preserves_legacy_demo_and_credentials(invoices, monkeypatch):
    from app import monday_seed
    from app.database.models import Invoice
    from tests.test_invoices import create

    client, factory, ids, _ = invoices
    old = create(client, ids)
    with factory() as db:
        user = db.get(User, ids["users"][0])
        user.email = monday_seed.DEMO_EMAIL
        user.firm_id = None
        user.password_hash = "synthetic-preserve"
        # Reproduce the existing demo's individual issuer scope.
        from app.database.models import InvoiceIssuer

        db.add(InvoiceIssuer(id=user.id, auditor_id=user.id, next_number=2))
        db.flush()
        db.get(Invoice, old["id"]).issuer_id = user.id
        db.commit()
    monkeypatch.setattr(monday_seed, "get_session_factory", lambda: factory)
    invoice_id = monday_seed.seed()
    assert monday_seed.seed() == invoice_id
    shared = client.get(f"/auditor/invoices/{invoice_id}")
    assert shared.status_code == 200
    with factory() as db:
        user = db.get(User, ids["users"][0])
        invoice = db.get(Invoice, invoice_id)
        assert invoice.auditor_id != user.id
        assert db.get(Invoice, old["id"]).issuer_id == user.firm_id
        assert user.password_hash == "synthetic-preserve"
