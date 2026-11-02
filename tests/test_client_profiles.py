"""Synthetic client contracts, assignment boundaries and contact audit trail."""

from datetime import date

import pytest
from sqlalchemy import select

from app.database.models import AuditLog, ClientContact, ClientProfileDetails, Engagement
from tests.test_invoices import invoices as invoices


def test_client_shapes_contacts_and_dashboard_compatibility(invoices):
    client, factory, ids, _ = invoices
    firm_id = ids["firms"][2]
    with factory() as db:
        db.add(ClientProfileDetails(firm_id=firm_id, firm_type="Introducing", crd="12345"))
        db.commit()
    profiles = client.get("/auditor/clients")
    assert profiles.status_code == 200
    assert len(profiles.json()) == 1
    profile = profiles.json()[0]
    assert profile["id"] == firm_id
    assert profile["firmType"] == "Introducing" and profile["crd"] == "12345"
    assert profile["clearing"] == profile["state"] == ""
    # Other auditors' engagements in the SAME client firm must not leak.
    assert [e["engagementId"] for e in profile["engagements"]] == [ids["engagements"][0]]
    assert profile["engagements"][0]["signedOn"] is None
    assert client.get(f"/auditor/clients/{firm_id}").json() == profile
    contact = client.post(
        f"/auditor/clients/{firm_id}/contacts",
        json={
            "name": "Synthetic Contact",
            "title": "Compliance",
            "email": "contact@example.test",
            "phone": "",
        },
    )
    assert contact.status_code == 201, contact.text
    assert set(contact.json()) == {"id", "name", "title", "email", "phone", "primary"}
    assert contact.json()["primary"] is False
    assert client.get(f"/auditor/clients/{firm_id}").json()["contacts"] == [contact.json()]
    summary = client.get(f"/auditor/engagements/{ids['engagements'][0]}/summary")
    assert summary.status_code == 200
    assert set(summary.json()) == {
        "id",
        "clientId",
        "firmName",
        "period",
        "stage",
        "due",
        "lead",
        "reviewer",
        "partner",
    }
    assert summary.json()["clientId"] == firm_id
    assert summary.json()["reviewer"] == summary.json()["partner"] == ""
    dashboard = client.get("/auditor/engagements").json()
    assert len(dashboard) == 1
    assert dashboard[0]["id"] == ids["engagements"][0]
    assert "readiness" in dashboard[0] and "firmId" in dashboard[0]
    assert all(dashboard[0][k] == v for k, v in summary.json().items())
    with factory() as db:
        event = db.scalar(select(AuditLog).where(AuditLog.action == "client.contact_created"))
        assert event.firm_id == firm_id and event.actor_id == ids["users"][0]
        assert event.entity_id == contact.json()["id"]
        assert "email" not in event.details  # Minimal log metadata, not copied contact details.


@pytest.mark.parametrize("who", [0, 3])
def test_every_profile_path_denies_other_firms_and_clients(invoices, who):
    client, factory, ids, current = invoices
    other_firm = ids["firms"][3]
    with factory() as db:
        foreign = Engagement(
            firm_id=other_firm,
            auditor_id=ids["users"][1],
            review_period_start=date(2025, 1, 1),
            review_period_end=date(2025, 12, 31),
        )
        db.add(foreign)
        db.flush()
        foreign_id = foreign.id
        db.add(
            ClientContact(
                firm_id=other_firm,
                name="Private synthetic contact",
                title="",
                email="private@example.test",
                phone="",
            )
        )
        db.commit()
    current[0] = ids["users"][who]
    code = 403 if who == 3 else 404
    assert client.get(f"/auditor/clients/{other_firm}").status_code == code
    assert (
        client.post(
            f"/auditor/clients/{other_firm}/contacts",
            json={"name": "Denied", "title": "", "email": "denied@example.test", "phone": ""},
        ).status_code
        == code
    )
    assert client.get(f"/auditor/engagements/{foreign_id}/summary").status_code == code
    for path in ["/auditor/clients", "/auditor/engagements"]:
        result = client.get(path)
        assert result.status_code == (403 if who == 3 else 200)
        assert other_firm not in result.text and foreign_id not in result.text
        assert "Private synthetic contact" not in result.text
    with factory() as db:
        assert len(db.scalars(select(ClientContact)).all()) == 1
        assert (
            db.scalar(select(AuditLog).where(AuditLog.action == "client.contact_created")) is None
        )


def test_same_firm_unassigned_summary_and_revoked_assignment_are_denied(invoices):
    client, factory, ids, _ = invoices
    assert client.get(f"/auditor/engagements/{ids['engagements'][1]}/summary").status_code == 404
    with factory() as db:
        db.get(Engagement, ids["engagements"][0]).auditor_id = None
        db.commit()
    firm = ids["firms"][2]
    assert client.get("/auditor/clients").json() == []
    assert client.get("/auditor/engagements").json() == []
    assert client.get(f"/auditor/clients/{firm}").status_code == 404
    assert (
        client.post(
            f"/auditor/clients/{firm}/contacts",
            json={"name": "Denied", "title": "", "email": "denied@example.test", "phone": ""},
        ).status_code
        == 404
    )


def test_contact_validation_and_missing_profile_metadata(invoices):
    client, _, ids, _ = invoices
    firm = ids["firms"][2]
    profile = client.get(f"/auditor/clients/{firm}").json()
    assert [profile[k] for k in ["firmType", "crd", "clearing", "state"]] == ["", "", "", ""]
    valid = {"name": "Synthetic", "title": "", "email": "synthetic@example.test", "phone": ""}
    for changes in [
        {"name": " "},
        {"email": "invalid"},
        {"firmId": ids["firms"][3]},
        {"primary": True},
        {"phone": "x" * 81},
    ]:
        assert (
            client.post(f"/auditor/clients/{firm}/contacts", json=valid | changes).status_code
            == 422
        )
