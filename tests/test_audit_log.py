"""Synthetic audit chain, immutability, API authorization and signoff tests."""

import pytest

# Imported pytest fixture is intentionally injected by name.
# ruff: noqa: F811
from sqlalchemy import delete, select, text, update

from app.audit import verify
from app.database.models import AuditLog, Engagement, EngagementStatus
from tests.test_backend_api import backend, sign_in_auditor, sign_in_client  # noqa: F401, F811


def test_append_and_verify_tamper(backend):
    client, factory, ids, _, _ = backend
    sign_in_client(client)
    client.get("/engagements/current")
    with factory() as db:
        rows = db.scalars(
            select(AuditLog).where(AuditLog.firm_id == ids["firm_a"]).order_by(AuditLog.sequence)
        ).all()
        assert len(rows) >= 2
        assert verify(rows)["valid"]
        assert rows[1].previous_hash == rows[0].row_hash
        victim = rows[0].id
    with factory() as db:
        # Simulate privileged tampering on SQLite (Postgres trigger blocks this).
        db.execute(text("UPDATE audit_logs SET action='tampered' WHERE id=:id"), {"id": victim})
        db.commit()
        rows = db.scalars(
            select(AuditLog).where(AuditLog.firm_id == ids["firm_a"]).order_by(AuditLog.sequence)
        ).all()
        assert not verify(rows)["valid"]


@pytest.mark.parametrize("operation", ["edit", "delete", "bulk_edit", "bulk_delete"])
def test_immutable(backend, operation):
    client, factory, ids, _, _ = backend
    sign_in_client(client)
    with factory() as db:
        row = db.scalar(select(AuditLog))
        with pytest.raises(ValueError, match="append-only"):
            if operation == "edit":
                row.action = "changed"
            elif operation == "delete":
                db.delete(row)
            elif operation == "bulk_edit":
                db.execute(update(AuditLog).values(action="changed"))
            else:
                db.execute(delete(AuditLog))
            db.commit()


@pytest.mark.parametrize("suffix", ["", "/verify-chain"])
def test_audit_api_tenant_and_role_isolation(backend, suffix):
    client, factory, ids, _, _ = backend
    path = "/auditor/audit-log" + suffix
    assert client.get(path, params={"firm_id": ids["firm_a"]}).status_code == 401
    sign_in_client(client)
    assert client.get(path, params={"firm_id": ids["firm_a"]}).status_code == 403
    client.cookies.clear()
    sign_in_auditor(client)
    with factory() as db:
        db.get(Engagement, ids["engagement_b"]).auditor_id = None
        db.commit()
    assert client.get(path, params={"firm_id": ids["firm_b"]}).status_code == 404
    assert client.get(path, params={"firm_id": ids["firm_a"]}).status_code == 200


def test_filters_pagination_and_verification(backend):
    client, _, ids, _, _ = backend
    sign_in_client(client)
    client.get("/engagements/current")
    client.cookies.clear()
    sign_in_auditor(client)
    path = "/auditor/audit-log"
    params = {"firm_id": ids["firm_a"], "limit": 1}
    first = client.get(path, params=params).json()
    second = client.get(path, params={**params, "offset": 1}).json()
    assert first["has_more"]
    assert first["items"][0]["id"] != second["items"][0]["id"]
    filtered = client.get(path, params={**params, "action": "engagement.view"}).json()
    assert filtered["items"][0]["action"] == "engagement.view"
    assert client.get(path, params={**params, "limit": 101}).status_code == 422
    result = client.get(path + "/verify-chain", params={"firm_id": ids["firm_a"]}).json()
    assert result["valid"] and result["checked"] >= 2
    assert (
        client.get(path, params={**params, "engagement_id": ids["engagement_b"]}).status_code == 404
    )
    scoped = client.get(path, params={**params, "engagement_id": ids["engagement_a"]}).json()
    assert scoped["items"][0]["action"] == "engagement.view"


def test_explicit_report_signoff_and_cross_tenant_denial(backend):
    client, factory, ids, _, _ = backend
    sign_in_auditor(client)
    payload = {"reportSha256": "a" * 64, "attestation": True}
    with factory() as db:
        db.get(Engagement, ids["engagement_b"]).auditor_id = None
        db.commit()
    other = f"/auditor/engagements/{ids['engagement_b']}/report/signoff"
    assert client.post(other, json=payload).status_code == 404
    path = f"/auditor/engagements/{ids['engagement_a']}/report/signoff"
    assert client.post(path, json=payload).status_code == 409
    with factory() as db:
        db.get(Engagement, ids["engagement_a"]).status = EngagementStatus.AWAITING_SIGNATURE
        db.commit()
    assert client.post(path, json={**payload, "attestation": False}).status_code == 422
    assert client.post(path, json=payload).status_code == 200
    with factory() as db:
        event = db.scalar(
            select(AuditLog).where(
                AuditLog.firm_id == ids["firm_a"], AuditLog.action == "report.signoff"
            )
        )
        assert event.actor_id == ids["auditor"]
        assert event.details["report_sha256"] == "a" * 64
