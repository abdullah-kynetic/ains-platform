"""L2-8: one journey across the new routes: test, review, find, reply, sign, confirm, invoice.

Steps that earlier test files already cover in depth (dispatch, upload, N/A, issue threads) are
not repeated. This proves the pieces join: the signed report is what the client confirms, and
that confirmation is what lets the auditor issue the invoice.
"""

from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.database.models import AuditLog, EngagementSignoff, ResponseRequest, User
from tests.test_backend_api import backend, sign_in_auditor, sign_in_client  # noqa: F401
from tests.test_findings import _body
from tests.test_findings import _document as _cited_document
from tests.test_signoff import NO, _conclude_all, _partner
from tests.test_workpapers_samples import REQUEST, _sign_in, _teammates


def test_journey_from_testing_to_invoice(backend):  # noqa: F811
    client, factory, ids, *_ = backend
    _teammates(factory, ids)
    _partner(factory, ids)
    eid = ids["engagement_a"]
    audit = f"/auditor/engagements/{eid}"

    # 1. The assigned auditor records conclusions, a workpaper and a finding.
    sign_in_auditor(client)
    _conclude_all(factory, ids)
    _cited_document(factory, ids)
    wp = client.put(
        f"{audit}/workpapers/{REQUEST}",
        json={"procedure": "Read the program.", "evidenceIds": [], "conclusion": "pass"},
    )
    assert wp.status_code == 200
    finding = client.post(f"{audit}/findings", json=_body()).json()
    assert (
        client.post(
            f"/auditor/findings/{finding['id']}/status", json={"status": "approved"}
        ).status_code
        == 200
    )
    assert (
        client.post(
            f"/auditor/findings/{finding['id']}/response-request",
            json={
                "title": "Alert closures",
                "requestText": "Please describe how alerts are closed.",
            },
        ).status_code
        == 201
    )
    assert client.put(f"{audit}/independence", json={"answers": NO}).status_code == 200

    # 2. The client answers the released request; the finding becomes "responded".
    sign_in_client(client)
    rid = client.get(f"/engagements/{eid}/response-requests").json()[0]["id"]
    assert (
        client.post(
            f"/engagements/{eid}/response-requests/{rid}/response", json={"text": "We will fix it."}
        ).status_code
        == 200
    )
    assert client.get(f"/engagements/{eid}/signed-report").json()["available"] is False

    # 3. Blockers remain until the workpaper is reviewed by someone else.
    _sign_in(client, "reviewer-a@example.test")
    blockers = client.get(f"{audit}/signoff/blockers").json()
    assert any("workpaper" in b for b in blockers)
    assert client.post(f"{audit}/signoff/review", json={}).status_code == 409
    assert client.post(f"{audit}/workpapers/{REQUEST}/review", json={}).status_code == 200
    assert client.get(f"{audit}/signoff/blockers").json() == []
    assert client.post(f"{audit}/signoff/review", json={"note": "Reviewed."}).status_code == 200

    # 4. The partner signs and the engagement is completed.
    _sign_in(client, "partner-a@example.test")
    signed = client.post(f"{audit}/signoff/partner", json={"typedName": "Pat Partner"}).json()
    fingerprint = signed["partner"]["fingerprint"]
    assert client.post(f"{audit}/complete").status_code == 200

    # 5. The client reads the signed report (no findings), then confirms it by fingerprint.
    sign_in_client(client)
    report = client.get(f"/engagements/{eid}/signed-report")
    assert report.json()["available"] is True and report.json()["confirmed"] is False
    assert "FINDING-INTERNAL" not in report.text
    confirm = f"/engagements/{eid}/signed-report/confirm"
    assert client.post(confirm, json={"fingerprint": "a" * 64}).status_code == 409
    assert client.post(confirm, json={"fingerprint": "nope"}).status_code == 422
    done = client.post(confirm, json={"fingerprint": fingerprint})
    assert done.status_code == 200 and done.json()["confirmed"] is True
    assert client.post(confirm, json={"fingerprint": fingerprint}).json()["confirmed"] is True

    # 6. Only now can the auditor issue an invoice for this engagement.
    sign_in_auditor(client)
    today = datetime.now(UTC).date()
    payload = {
        "firmId": ids["firm_a"],
        "engagementId": eid,
        "issueDate": str(today),
        "dueDate": str(today + timedelta(days=30)),
        "lineItems": [{"description": "Synthetic review", "quantity": "1", "rateCents": 1000}],
    }
    invoice = client.post("/auditor/invoices", json=payload).json()
    assert client.post(f"/auditor/invoices/{invoice['id']}/sent").status_code == 200
    sign_in_client(client)
    listed = client.get(f"/engagements/{eid}/invoices").json()
    assert [i["status"] for i in listed] == ["sent"]

    with factory() as db:
        assert db.scalar(select(EngagementSignoff.partner_fingerprint)) == fingerprint
        row = db.scalar(select(AuditLog).where(AuditLog.action == "report.confirmed"))
        assert row.details["fingerprint"] == fingerprint and row.firm_id == ids["firm_a"]
        assert db.scalar(select(ResponseRequest.status)) == "responded"
        assert db.scalar(select(User.id).where(User.email == "partner-a@example.test"))
