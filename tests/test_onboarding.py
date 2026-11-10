"""Authenticated per-user walkthrough persistence and demo-only reset."""

import pytest
from sqlalchemy import select

from app.database.models import AuditLog, User
from tests.test_backend_api import backend as backend
from tests.test_backend_api import sign_in_auditor, sign_in_client
from tests.test_invoices import invoices as invoices


def test_finish_refreshes_a_user_loaded_before_another_request_finished(backend):
    from app.auth.onboarding import FinishOnboarding, finish

    _, factory, ids, _, _ = backend
    with factory() as stale_db:
        stale_user = stale_db.get(User, ids["client_a"])
        assert stale_user.onboarding_state is None
        with factory() as first_db:
            first_user = first_db.get(User, ids["client_a"])
            finish(FinishOnboarding(action="completed"), first_user, first_db)
            first_db.refresh(first_user)
            finished_at = first_user.onboarding_finished_at
        result = finish(FinishOnboarding(action="skipped"), stale_user, stale_db)
        assert result["state"] == "completed"
        assert stale_user.onboarding_finished_at == finished_at
    with factory() as db:
        assert db.get(User, ids["client_a"]).onboarding_state == "completed"
        assert (
            len(
                db.scalars(
                    select(AuditLog).where(
                        AuditLog.actor_id == ids["client_a"], AuditLog.action.like("onboarding.%")
                    )
                ).all()
            )
            == 1
        )


@pytest.mark.parametrize("role", ["client", "auditor"])
@pytest.mark.parametrize("action", ["completed", "skipped"])
def test_session_onboarding_is_terminal_across_new_logins(backend, role, action):
    client, factory, ids, _, _ = backend
    login = sign_in_client if role == "client" else sign_in_auditor
    login(client)
    assert client.get("/auth/session").json()["user"]["onboarding_state"] is None
    assert client.post("/auth/onboarding", json={"action": action}).json()["state"] == action
    user_id = ids["client_a"] if role == "client" else ids["auditor"]
    with factory() as db:
        finished_at = db.get(User, user_id).onboarding_finished_at
        assert finished_at is not None
    # A retry or a different final action cannot overwrite the first decision/time.
    other_action = "skipped" if action == "completed" else "completed"
    assert client.post("/auth/onboarding", json={"action": other_action}).json()["state"] == action
    assert client.get("/auth/session").json()["user"]["onboarding_state"] == action
    assert client.post("/auth/sign-out").status_code == 204
    assert client.get("/auth/session").status_code == 401
    client.cookies.clear()
    login(client)
    assert client.get("/auth/session").json()["user"]["onboarding_state"] == action
    assert client.get("/auth/onboarding").json()["state"] == action
    # A separate cookie jar represents a new browser/device; state belongs to the user.
    from starlette.testclient import TestClient

    with TestClient(client.app) as fresh:
        login(fresh)
        assert fresh.get("/auth/session").json()["user"]["onboarding_state"] == action
    with factory() as db:
        assert db.get(User, user_id).onboarding_finished_at == finished_at
        events = db.scalars(
            select(AuditLog).where(
                AuditLog.actor_id == user_id, AuditLog.action.like("onboarding.%")
            )
        ).all()
        assert len(events) == 1


def test_invite_accepted_user_starts_pending_in_session_and_password_login(backend):
    from tests.test_backend_api import invitation_token

    client, factory, ids, _, _ = backend
    sign_in_auditor(client)
    created = client.post(
        f"/auditor/engagements/{ids['engagement_a']}/invitations",
        json={"email": "synthetic-onboarding@example.test", "name": "Synthetic Onboarding Client"},
    )
    assert created.status_code == 201
    client.cookies.clear()
    accepted = client.post(
        "/auth/invitations/accept",
        json={"token": invitation_token(created.json()), "password": "synthetic-password-123"},
    )
    assert accepted.status_code == 200
    user = accepted.json()["user"]
    assert user["onboarding_state"] is None
    assert client.get("/auth/session").json()["user"]["onboarding_state"] is None
    client.cookies.clear()
    signed_in = client.post(
        "/auth/password",
        json={"email": "synthetic-onboarding@example.test", "password": "synthetic-password-123"},
    )
    assert signed_in.status_code == 200
    assert signed_in.json()["user"]["onboarding_state"] is None
    with factory() as db:
        assert db.get(User, user["id"]).onboarding_finished_at is None


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
