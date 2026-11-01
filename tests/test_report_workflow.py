"""Report persistence, rich-text safety, final locks and server-side authorization."""

import pytest
from sqlalchemy import select

from app.checklist import ClientStatus
from app.checklist.catalog import initialize_engagement
from app.database.models import AuditLog, Engagement, EngagementReport, FindingDraft, ReviewState
from app.reports.workflow import sanitize
from tests.test_invoices import invoices as invoices


def create(client, ids):
    response = client.post("/auditor/reports", json={"engagement_id": ids["engagements"][0]})
    assert response.status_code == 201, response.text
    return response.json()


def test_report_prefill_edit_finalize_lock_reopen_and_audit(invoices):
    client, factory, ids, _ = invoices
    with factory() as db:
        engagement = db.get(Engagement, ids["engagements"][0])
        initialize_engagement(engagement)
        engagement.items[0].status = ClientStatus.NOT_APPLICABLE
        db.add(
            FindingDraft(
                firm_id=engagement.firm_id,
                engagement_id=engagement.id,
                title="Synthetic reviewed finding",
                body="Synthetic narrative",
                severity="low",
                review_state=ReviewState.ACCEPTED,
                citations=[],
            )
        )
        db.commit()
    report = create(client, ids)
    assert create(client, ids)["id"] == report["id"]
    assert len(report["snapshot"]["requests"]) == 34
    assert report["snapshot"]["requests"][0]["status"] == "not_applicable"
    assert "Synthetic narrative" in report["content"]["sections"][2]["html"]
    path = f"/auditor/reports/{report['id']}"
    content = report["content"]
    content["sections"][0]["html"] = (
        '<p onclick="bad()"><strong>Human scope</strong>'
        '<script>bad()</script><img src=x onerror=bad()></p>'
    )
    content["item_findings"]["AML-BD-001"] = "Synthetic per-item finding"
    saved = client.patch(path, json={"version": report["version"], "content": content})
    assert saved.status_code == 200
    report = saved.json()
    assert report["content"]["sections"][0]["html"] == "<p><strong>Human scope</strong></p>"
    assert client.get(path).json()["content"] == report["content"]
    assert client.patch(path, json={"version": 1, "content": content}).status_code == 409
    assert (
        client.post(
            path + "/finalize", json={"version": report["version"], "attestation": False}
        ).status_code
        == 422
    )
    final = client.post(
        path + "/finalize", json={"version": report["version"], "attestation": True}
    ).json()
    assert final["status"] == "final" and len(final["contentSha256"]) == 64
    assert (
        client.patch(path, json={"version": final["version"], "content": content}).status_code
        == 409
    )
    reopened = client.post(path + "/reopen", json={"version": final["version"]}).json()
    assert reopened["status"] == "draft" and reopened["contentSha256"] is None
    assert (
        client.patch(path, json={"version": reopened["version"], "content": content}).status_code
        == 200
    )
    with factory() as db:
        events = db.scalars(select(AuditLog).where(AuditLog.action.like("report.%"))).all()
        assert [e.action for e in events] == [
            "report.created",
            "report.updated",
            "report.finalized",
            "report.reopened",
            "report.updated",
        ]
        assert events[2].details["content_sha256"] == final["contentSha256"]


@pytest.mark.parametrize("who", [1, 2, 3])
def test_all_report_paths_deny_unassigned_auditors_other_firms_and_clients(invoices, who):
    client, _, ids, current = invoices
    report = create(client, ids)
    current[0] = ids["users"][who]
    denied = 403 if who == 3 else 404
    path = f"/auditor/reports/{report['id']}"
    assert client.get(path).status_code == denied
    assert (
        client.patch(path, json={"version": 1, "content": report["content"]}).status_code == denied
    )
    for action in ["finalize", "reopen"]:
        assert (
            client.post(path + "/" + action, json={"version": 1, "attestation": True}).status_code
            == denied
        )
    assert (
        client.post("/auditor/reports", json={"engagement_id": report["engagementId"]}).status_code
        == denied
    )
    listing = client.get("/auditor/reports")
    assert listing.status_code == (403 if who == 3 else 200)
    if who != 3:
        assert listing.json() == []


def test_reports_reject_restricted_content_invalid_requests_and_assignment_revocation(invoices):
    client, factory, ids, _ = invoices
    report = create(client, ids)
    path = f"/auditor/reports/{report['id']}"
    for request in ["AML-BD-017", "AML-BD-025", "wrong"]:
        content = {**report["content"], "item_findings": {request: "Synthetic forbidden text"}}
        assert client.patch(path, json={"version": 1, "content": content}).status_code == 422
    with factory() as db:
        db.get(Engagement, ids["engagements"][0]).auditor_id = ids["users"][2]
        db.commit()
    assert client.get(path).status_code == 404
    assert client.get("/auditor/reports").json() == []


def test_report_seed_is_idempotent_and_does_not_touch_users(invoices, monkeypatch):
    from app import report_seed
    from app.database.models import User

    _, factory, ids, _ = invoices
    monkeypatch.setattr(report_seed, "get_session_factory", lambda: factory)
    with factory() as db:
        user = db.get(User, ids["users"][0])
        user.email = report_seed.DEMO_EMAIL
        user.password_hash = "synthetic-preserve"
        db.commit()
    assert report_seed.seed() == report_seed.seed()
    with factory() as db:
        assert len(db.scalars(select(EngagementReport)).all()) == 1
        assert db.get(User, ids["users"][0]).password_hash == "synthetic-preserve"


@pytest.mark.parametrize(
    "html",
    [
        "<svg/onload=bad()>",
        "<iframe src=x>bad</iframe>",
        "<style>bad</style>",
        '<a href="javascript:bad()">safe</a>',
        "<img src=x onerror=bad()>",
    ],
)
def test_rich_text_has_no_executable_markup(html):
    result = sanitize(html)
    assert "<svg" not in result and "<iframe" not in result and "<style" not in result
    assert "<a " not in result and "<img" not in result and "javascript:" not in result
