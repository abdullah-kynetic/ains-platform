"""Quentin's workflow: dispatch, reasoned N/A, document numbers, links, issue threads, report
confirmation, invoice gate and stage pipeline. Synthetic data only.

Every route is also covered by the generic sweeps (session required, role gates, cross-tenant
denial, unassigned-auditor denial). The tests here use REAL foreign ids so a 404 can only come
from the firm / assignment filters.
"""

import json
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.checklist import ClientStatus
from app.database.models import (
    AuditLog,
    ChecklistItemInstance,
    Document,
    DocumentIssue,
    Engagement,
    EngagementStatus,
    Invoice,
)
from tests.test_backend_api import backend, sign_in_auditor, sign_in_client  # noqa: F401

FORBIDDEN = {
    "findings",
    "severity",
    "citations",
    "internalNotes",
    "internal_notes",
    "assessment",
    "findingId",
    "notes",
    "checkResults",
}
BETA = "beta-client@example.test"


def keys(value):
    if isinstance(value, dict):
        for key, child in value.items():
            yield key
            yield from keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from keys(child)


def base(ids, who="auditor", eid="engagement_a"):
    return f"{'/auditor' if who == 'auditor' else ''}/engagements/{ids[eid]}"


def as_client(client, email="alpha-client@example.test"):
    client.cookies.clear()
    sign_in_client(client, email)


def as_auditor(client):
    client.cookies.clear()
    sign_in_auditor(client)


def upload(client, ids, name="synthetic.txt", item=None):
    path = f"/engagements/{ids['engagement_a']}" + (f"/items/{ids[item]}" if item else "")
    response = client.post(
        f"{path}/documents", files={"file": (name, name.encode() + b" body", "text/plain")}
    )
    assert response.status_code == 201, response.text
    return response.json()


def real_workflow_rows(factory, ids):
    """A real document and open issue in firm A for id-scoped denial checks."""
    with factory() as db:
        document = Document(
            firm_id=ids["firm_a"],
            engagement_id=ids["engagement_a"],
            item_instance_id=ids["item_a"],
            uploaded_by_id=ids["client_a"],
            original_name="synthetic-proof.txt",
            size_bytes=3,
            egnyte_path="/synthetic/proof",
            sha256="b" * 64,
            version="1",
            number="1.1",
        )
        db.add(document)
        db.get(Engagement, ids["engagement_a"]).document_seq += 1
        document.number = f"1.{db.get(Engagement, ids['engagement_a']).document_seq}"
        db.flush()
        issue = DocumentIssue(
            firm_id=ids["firm_a"],
            engagement_id=ids["engagement_a"],
            item_instance_id=ids["item_a"],
            document_id=document.id,
            kind="incorrect",
            created_by_id=ids["auditor"],
        )
        db.add(issue)
        db.flush()
        from app.database.models import IssueMessage

        db.add(
            IssueMessage(
                firm_id=ids["firm_a"],
                issue_id=issue.id,
                author_id=ids["auditor"],
                author_role="auditor",
                body="Synthetic request.",
            )
        )
        db.commit()
        return {"document_id": document.id, "issue_id": issue.id, "request_id": "AML-BD-004"}


def actions(factory):
    with factory() as db:
        return [a.action for a in db.scalars(select(AuditLog).order_by(AuditLog.sequence))]


# --- dispatch -----------------------------------------------------------------------------


def test_send_checklist_records_dispatch_once_and_moves_the_stage(backend):  # noqa: F811
    client, factory, ids, *_ = backend
    with factory() as db:
        db.get(Engagement, ids["engagement_a"]).status = EngagementStatus.DRAFT
        db.commit()
    as_auditor(client)
    assert client.get(f"{base(ids)}/progress").json()["stage"] == "not_sent"
    response = client.post(f"{base(ids)}/checklist/send")
    assert response.status_code == 200 and response.json()["stage"] == "checklist_sent"
    assert client.post(f"{base(ids)}/checklist/send").status_code == 409
    with factory() as db:
        engagement = db.get(Engagement, ids["engagement_a"])
        assert engagement.checklist_sent_at and engagement.checklist_sent_by_id == ids["auditor"]
        assert engagement.status == EngagementStatus.COLLECTING
    assert actions(factory).count("checklist.sent") == 1


def test_send_checklist_requires_initialized_items_and_assignment(backend):  # noqa: F811
    client, factory, ids, *_ = backend
    with factory() as db:
        db.query(ChecklistItemInstance).filter_by(engagement_id=ids["engagement_a"]).delete()
        db.commit()
    as_auditor(client)
    assert client.post(f"{base(ids)}/checklist/send").status_code == 409
    with factory() as db:
        db.get(Engagement, ids["engagement_a"]).auditor_id = ids["enrolling_auditor"]
        db.commit()
    assert client.post(f"{base(ids)}/checklist/send").status_code == 404
    as_client(client)
    assert client.post(f"{base(ids)}/checklist/send").status_code == 403


# --- reasoned N/A -------------------------------------------------------------------------


def test_reasoned_na_request_accept_sorts_last_keeps_number_and_undo_restores(backend):  # noqa: F811
    client, factory, ids, *_ = backend
    as_client(client)
    path = f"{base(ids, 'client')}/items/{ids['item_a']}"
    assert client.post(f"{path}/na-request", json={"reason": "no"}).status_code == 422
    assert client.post(f"{path}/na-request", json={}).status_code == 422
    ok = client.post(f"{path}/na-request", json={"reason": "We do not offer this product."})
    assert ok.status_code == 200 and ok.json() == {"state": "pending"}
    assert client.post(f"{path}/na-request", json={"reason": "again please"}).status_code == 409
    progress = client.get(f"{base(ids, 'client')}/progress").json()
    row = next(i for i in progress["items"] if i["id"] == ids["item_a"])
    assert row["status"] == "not_started" and row["naRequest"]["state"] == "pending"
    assert progress["counts"]["naPending"] == 1
    assert client.post(f"{path}/submit").status_code == 409  # waits for the auditor
    as_auditor(client)
    decision = f"{base(ids)}/items/{ids['item_a']}/na-request/decision"
    assert client.post(decision, json={"decision": "accept"}).status_code == 200
    assert client.post(decision, json={"decision": "accept"}).status_code == 409
    progress = client.get(f"{base(ids)}/progress").json()
    numbers = [i["number"] for i in progress["items"]]
    last = progress["items"][-1]
    assert last["id"] == ids["item_a"] and last["status"] == "na"
    assert last["number"] == 4 and last["naRequest"]["state"] == "accepted"
    assert numbers[:-1] == sorted(numbers[:-1])
    assert (
        client.post(
            f"{base(ids)}/items/{ids['item_a']}/na", json={"not_applicable": False}
        ).status_code
        == 200
    )
    with factory() as db:
        item = db.get(ChecklistItemInstance, ids["item_a"])
        assert item.status == ClientStatus.REQUESTED
        assert item.na_review_state.value == "pending"  # undo restores the previous state
    log = actions(factory)
    assert {"request.na_requested", "request.na_accepted", "request.na_unset"} <= set(log)


def test_na_rejection_needs_a_note_and_client_can_ask_again(backend):  # noqa: F811
    client, factory, ids, *_ = backend
    as_client(client)
    path = f"{base(ids, 'client')}/items/{ids['item_a']}"
    client.post(f"{path}/na-request", json={"reason": "We do not offer this product."})
    as_auditor(client)
    decision = f"{base(ids)}/items/{ids['item_a']}/na-request/decision"
    assert client.post(decision, json={"decision": "reject"}).status_code == 422
    assert client.post(decision, json={"decision": "reject", "note": "We saw it offered."})
    as_client(client)
    row = next(
        i
        for i in client.get(f"{base(ids, 'client')}/progress").json()["items"]
        if i["id"] == ids["item_a"]
    )
    assert row["status"] == "not_started"
    assert row["naRequest"] == {
        "state": "rejected",
        "reason": "We do not offer this product.",
        "decisionNote": "We saw it offered.",
        "requestedAt": row["naRequest"]["requestedAt"],
    }
    assert (
        client.post(f"{path}/na-request", json={"reason": "Here is more detail."}).status_code
        == 200
    )


def test_client_cannot_declare_na_directly_or_for_restricted_items(backend):  # noqa: F811
    client, factory, ids, *_ = backend
    as_client(client)
    assert (
        client.post(
            f"{base(ids, 'client')}/items/{ids['item_a']}/na", json={"not_applicable": True}
        ).status_code
        == 409
    )
    restricted = f"{base(ids, 'client')}/items/{ids['restricted_a']}"
    assert (
        client.post(f"{restricted}/na-request", json={"reason": "Not relevant."}).status_code == 409
    )
    as_auditor(client)
    decision = f"{base(ids)}/items/{ids['item_a']}/na-request/decision"
    assert client.post(decision, json={"decision": "accept"}).status_code == 409  # nothing pending


def test_na_request_is_denied_across_firms_and_unassigned_auditors(backend):  # noqa: F811
    client, factory, ids, *_ = backend
    as_client(client)
    client.post(
        f"{base(ids, 'client')}/items/{ids['item_a']}/na-request",
        json={"reason": "We do not offer this product."},
    )
    as_client(client, BETA)
    path = f"{base(ids, 'client')}/items/{ids['item_a']}/na-request"
    assert client.post(path, json={"reason": "We do not offer this."}).status_code == 404
    as_auditor(client)
    with factory() as db:
        db.get(Engagement, ids["engagement_a"]).auditor_id = ids["enrolling_auditor"]
        db.commit()
    decision = f"{base(ids)}/items/{ids['item_a']}/na-request/decision"
    assert client.post(decision, json={"decision": "accept"}).status_code == 404


# --- document numbers, links, submit ------------------------------------------------------


def test_document_numbers_are_stable_sequential_and_per_engagement(backend):  # noqa: F811
    client, factory, ids, *_ = backend
    as_client(client)
    first = upload(client, ids, "one.txt", item="item_a")
    second = upload(client, ids, "two.txt")
    third = upload(client, ids, "three.txt", item="item_a")
    assert [first["number"], second["number"], third["number"]] == ["1.1", "1.2", "1.3"]
    current = client.get("/engagements/current").json()
    numbers = {f["number"] for s in current["sections"] for i in s["items"] for f in i["files"]} | {
        f["number"] for f in current["unassignedDocuments"]
    }
    assert numbers == {"1.1", "1.2", "1.3"}
    as_auditor(client)
    workspace = client.get(f"{base(ids)}/workspace").json()
    assert {d["number"] for r in workspace["requests"] for d in r["documents"]} == {"1.1", "1.3"}
    with factory() as db:
        assert db.get(Engagement, ids["engagement_a"]).document_seq == 3
        assert db.get(Engagement, ids["engagement_b"]).document_seq == 0


def test_link_unlink_and_submit_item_and_checklist(backend):  # noqa: F811
    client, factory, ids, *_ = backend
    as_client(client)
    item = f"{base(ids, 'client')}/items/{ids['item_a']}"
    assert client.post(f"{item}/submit").status_code == 409  # no document yet
    receipt = upload(client, ids, "receipt.txt")
    link = f"{item}/documents/{receipt['id']}/link"
    assert client.post(link).json()["number"] == "1.1"
    assert client.post(link).status_code == 200  # idempotent
    progress = client.get(f"{base(ids, 'client')}/progress").json()
    row = next(i for i in progress["items"] if i["id"] == ids["item_a"])
    assert [d["number"] for d in row["documents"]] == ["1.1"]
    assert client.post(f"{item}/documents/unknown-id/link").status_code == 404
    assert client.delete(f"{item}/documents/unknown-id/link").status_code == 404
    assert client.delete(link).status_code == 200
    assert client.post(f"{item}/submit").status_code == 409
    assert client.post(link).status_code == 200
    assert client.post(f"{item}/submit").json()["status"] == "submitted"
    row = next(
        i
        for i in client.get(f"{base(ids, 'client')}/progress").json()["items"]
        if i["id"] == ids["item_a"]
    )
    assert row["status"] == "submitted"
    assert client.post(f"{base(ids, 'client')}/submit").status_code == 200
    with factory() as db:
        engagement = db.get(Engagement, ids["engagement_a"])
        assert engagement.client_submitted_at is not None
    assert client.get(f"{base(ids, 'client')}/progress").json()["stage"] == "under_review"
    assert {
        "document.linked",
        "document.unlinked",
        "request.submitted",
        "checklist.submitted",
    } <= set(actions(factory))


def test_link_is_denied_for_foreign_documents_and_restricted_items(backend):  # noqa: F811
    client, factory, ids, *_ = backend
    rows = real_workflow_rows(factory, ids)
    as_client(client, BETA)
    foreign = f"{base(ids, 'client')}/items/{ids['item_a']}/documents/{rows['document_id']}/link"
    assert client.post(foreign).status_code == 404
    assert client.delete(foreign).status_code == 404
    as_client(client)
    restricted = (
        f"{base(ids, 'client')}/items/{ids['restricted_a']}/documents/{rows['document_id']}"
    )
    assert client.post(f"{restricted}/link").status_code == 409


def test_accept_item_needs_submission_and_closes_the_checklist_state(backend):  # noqa: F811
    client, factory, ids, *_ = backend
    as_auditor(client)
    accept = f"{base(ids)}/items/{ids['item_a']}/accept"
    assert client.post(accept).status_code == 409  # not submitted
    as_client(client)
    upload(client, ids, "doc.txt", item="item_a")
    assert client.post(f"{base(ids, 'client')}/items/{ids['item_a']}/submit").status_code == 200
    as_auditor(client)
    assert client.post(accept).json()["status"] == "accepted"
    row = next(
        i for i in client.get(f"{base(ids)}/progress").json()["items"] if i["id"] == ids["item_a"]
    )
    assert row["status"] == "accepted"


# --- issue flags and threads --------------------------------------------------------------


def test_flag_creates_thread_with_replies_reupload_and_explicit_resolution(backend):  # noqa: F811
    client, factory, ids, *_ = backend
    as_client(client)
    first = upload(client, ids, "bank-2023.txt", item="item_a")
    client.post(f"{base(ids, 'client')}/items/{ids['item_a']}/submit")
    as_auditor(client)
    flag = f"{base(ids)}/items/{ids['item_a']}/issues"
    assert (
        client.post(
            flag, json={"kind": "bogus", "documentId": first["id"], "note": "x"}
        ).status_code
        == 422
    )
    assert client.post(flag, json={"kind": "wrong_year", "note": "Wrong year."}).status_code == 422
    opened = client.post(
        flag,
        json={
            "kind": "wrong_year",
            "documentId": first["id"],
            "note": "This is the 2023 statement.",
        },
    )
    assert opened.status_code == 201, opened.text
    issue = opened.json()
    assert issue["status"] == "open" and issue["document"]["number"] == "1.1"
    assert issue["awaiting"] == "client" and len(issue["messages"]) == 1
    progress = client.get(f"{base(ids)}/progress").json()
    row = next(i for i in progress["items"] if i["id"] == ids["item_a"])
    assert row["status"] == "needs_info" and row["openIssues"] == 1
    assert progress["stage"] == "info_requested"
    assert client.post(f"{base(ids)}/items/{ids['item_a']}/accept").status_code == 409
    # client sees the thread and the item reason, never internal fields
    as_client(client)
    threads = client.get(f"{base(ids, 'client')}/issues").json()
    assert [t["id"] for t in threads] == [issue["id"]]
    assert not set(keys(threads)) & FORBIDDEN
    assert client.post(f"{base(ids, 'client')}/items/{ids['item_a']}/submit").status_code == 409
    fresh = upload(client, ids, "bank-2025.txt")
    reply = client.post(
        f"{base(ids, 'client')}/issues/{issue['id']}/replies",
        json={"body": "Here is the 2025 statement.", "documentId": fresh["id"]},
    )
    assert reply.status_code == 201
    assert reply.json()["awaiting"] == "auditor"
    assert reply.json()["messages"][-1]["documentNumber"] == "1.2"
    as_auditor(client)
    answer = client.post(
        f"{base(ids)}/issues/{issue['id']}/replies", json={"body": "Thanks, checking."}
    )
    assert answer.json()["awaiting"] == "client"
    still_open = client.get(f"{base(ids)}/progress").json()
    assert (
        next(i for i in still_open["items"] if i["id"] == ids["item_a"])["status"] == "needs_info"
    )
    resolved = client.post(f"{base(ids)}/issues/{issue['id']}/resolve", json={"note": "All good."})
    assert resolved.status_code == 200 and resolved.json()["status"] == "resolved"
    assert client.post(f"{base(ids)}/issues/{issue['id']}/resolve", json={}).status_code == 409
    assert (
        client.post(f"{base(ids)}/issues/{issue['id']}/replies", json={"body": "late"}).status_code
        == 409
    )
    after = client.get(f"{base(ids)}/progress").json()
    row = next(i for i in after["items"] if i["id"] == ids["item_a"])
    assert row["status"] == "submitted" and row["openIssues"] == 0
    assert [d["number"] for d in row["documents"]] == ["1.1", "1.2"]
    assert client.post(f"{base(ids)}/items/{ids['item_a']}/accept").status_code == 200
    log = actions(factory)
    assert {"document.issue_flagged", "issue.replied", "issue.resolved"} <= set(log)


def test_missing_flag_needs_no_document_and_marks_more_needed(backend):  # noqa: F811
    client, factory, ids, *_ = backend
    as_auditor(client)
    response = client.post(
        f"{base(ids)}/items/{ids['item_a']}/issues",
        json={"kind": "missing", "note": "Please send the signed page."},
    )
    assert response.status_code == 201 and response.json()["document"] is None
    with factory() as db:
        item = db.get(ChecklistItemInstance, ids["item_a"])
        assert item.status == ClientStatus.ACTION_NEEDED_MORE
        assert "signed page" not in (item.client_reason or "")


def test_issue_routes_deny_foreign_clients_unassigned_auditors_and_wrong_roles(backend):  # noqa: F811
    client, factory, ids, *_ = backend
    rows = real_workflow_rows(factory, ids)
    issue = rows["issue_id"]
    as_client(client, BETA)
    assert client.get(f"{base(ids, 'client')}/issues").status_code == 404
    reply = f"{base(ids, 'client')}/issues/{issue}/replies"
    assert client.post(reply, json={"body": "hello"}).status_code == 404
    as_client(client)
    assert (
        client.post(
            f"{base(ids)}/items/{ids['item_a']}/issues", json={"kind": "missing", "note": "x"}
        ).status_code
        == 403
    )
    assert client.post(f"{base(ids)}/issues/{issue}/resolve", json={}).status_code == 403
    # a real issue id of another firm's engagement is not reachable through your own engagement
    as_auditor(client)
    other = f"/auditor/engagements/{ids['engagement_b']}/issues/{issue}"
    assert client.post(f"{other}/resolve", json={}).status_code == 404
    assert client.post(f"{other}/replies", json={"body": "x"}).status_code == 404
    with factory() as db:
        db.get(Engagement, ids["engagement_a"]).auditor_id = ids["enrolling_auditor"]
        db.commit()
    assert client.get(f"{base(ids)}/issues").status_code == 404
    assert client.post(f"{base(ids)}/issues/{issue}/resolve", json={}).status_code == 404
    assert client.post(f"{base(ids)}/items/{ids['item_a']}/accept").status_code == 404
    assert (
        client.post(
            f"{base(ids)}/items/{ids['item_a']}/issues", json={"kind": "missing", "note": "x"}
        ).status_code
        == 404
    )


def test_flag_rejects_a_document_that_does_not_belong_to_the_item(backend):  # noqa: F811
    client, factory, ids, *_ = backend
    as_client(client)
    stray = upload(client, ids, "stray.txt")  # unassigned, not linked to item_a
    as_auditor(client)
    response = client.post(
        f"{base(ids)}/items/{ids['item_a']}/issues",
        json={"kind": "incorrect", "documentId": stray["id"], "note": "Looks wrong."},
    )
    assert response.status_code == 404
    with factory() as db:
        assert db.scalar(select(DocumentIssue)) is None


def test_reply_cannot_attach_a_document_from_another_engagement(backend):  # noqa: F811
    client, factory, ids, *_ = backend
    rows = real_workflow_rows(factory, ids)
    with factory() as db:
        foreign = Document(
            firm_id=ids["firm_b"],
            engagement_id=ids["engagement_b"],
            uploaded_by_id=ids["client_b"],
            original_name="beta.txt",
            size_bytes=1,
            egnyte_path="/synthetic/beta",
            sha256="c" * 64,
            version="1",
            number="1.1",
        )
        db.get(Engagement, ids["engagement_b"]).document_seq += 1
        db.add(foreign)
        db.commit()
        foreign_id = foreign.id
    as_client(client)
    response = client.post(
        f"{base(ids, 'client')}/issues/{rows['issue_id']}/replies",
        json={"body": "attached", "documentId": foreign_id},
    )
    assert response.status_code == 404


# --- report confirmation, invoice gate and stages -----------------------------------------


def finalize_report(client, ids, factory):
    as_auditor(client)
    created = client.post("/auditor/reports", json={"engagement_id": ids["engagement_a"]})
    assert created.status_code == 201, created.text
    report = created.json()
    done = client.post(
        f"/auditor/reports/{report['id']}/finalize",
        json={"version": report["version"], "attestation": True},
    )
    assert done.status_code == 200, done.text
    return done.json()


def test_client_report_confirmation_flow_gates_the_invoice(backend):  # noqa: F811
    client, factory, ids, *_ = backend
    as_client(client)
    report_path = f"{base(ids, 'client')}/report"
    assert client.get(report_path).status_code == 404  # nothing final yet
    final = finalize_report(client, ids, factory)
    today = datetime.now(UTC).date()
    invoice = client.post(
        "/auditor/invoices",
        json={
            "firmId": ids["firm_a"],
            "engagementId": ids["engagement_a"],
            "issueDate": str(today),
            "dueDate": str(today + timedelta(days=30)),
            "lineItems": [{"description": "Synthetic review", "quantity": "1", "rateCents": 1000}],
        },
    ).json()
    assert client.get(f"{base(ids)}/progress").json()["stage"] == "report_sent"
    # no invoice can be issued before the client confirms
    assert client.post(f"/auditor/invoices/{invoice['id']}/sent").status_code == 409
    assert (
        client.post(
            f"/auditor/reports/{final['id']}/reopen", json={"version": final["version"]}
        ).status_code
        == 200
    )
    final = client.post(
        f"/auditor/reports/{final['id']}/finalize",
        json={"version": final["version"] + 1, "attestation": True},
    ).json()
    as_client(client)
    view = client.get(report_path).json()
    assert set(view) == {
        "engagementId", "reportId", "sections", "finalizedAt", "contentSha256",
        "confirmed", "confirmedAt",
    }  # fmt: skip
    assert not set(keys(view)) & FORBIDDEN and view["confirmed"] is False
    from app.reports import ReportGenerator

    heading = ReportGenerator().template.findings_heading
    assert heading not in [section["title"] for section in view["sections"]]
    wrong = client.post(f"{report_path}/confirm", json={"contentSha256": "a" * 64})
    assert wrong.status_code == 409
    confirmed = client.post(
        f"{report_path}/confirm", json={"contentSha256": final["contentSha256"]}
    )
    assert confirmed.status_code == 200 and confirmed.json()["confirmed"] is True
    assert (
        client.post(
            f"{report_path}/confirm", json={"contentSha256": final["contentSha256"]}
        ).status_code
        == 200
    )
    assert actions(factory).count("report.confirmed") == 1  # idempotent, logged once
    as_auditor(client)
    assert (
        client.post(
            f"/auditor/reports/{final['id']}/reopen", json={"version": final["version"]}
        ).status_code
        == 409
    )
    assert client.get(f"{base(ids)}/progress").json()["stage"] == "confirmed"
    assert client.post(f"/auditor/invoices/{invoice['id']}/sent").status_code == 200
    assert client.get(f"{base(ids)}/progress").json()["stage"] == "invoiced"
    paid = client.post(
        f"/auditor/invoices/{invoice['id']}/paid",
        json={"amountCents": 1000, "paidDate": str(today)},
    )
    assert paid.status_code == 200
    assert client.get(f"{base(ids)}/progress").json()["stage"] == "paid"
    pipeline = client.get("/auditor/pipeline").json()
    mine = next(e for e in pipeline if e["id"] == ids["engagement_a"])
    assert mine["workflowStage"] == "paid"
    with factory() as db:
        assert db.scalar(select(Invoice.status)) == "paid"


def test_report_confirmation_is_firm_and_role_scoped(backend):  # noqa: F811
    client, factory, ids, *_ = backend
    final = finalize_report(client, ids, factory)
    as_client(client, BETA)
    path = f"{base(ids, 'client')}/report"
    assert client.get(path).status_code == 404
    assert (
        client.post(f"{path}/confirm", json={"contentSha256": final["contentSha256"]}).status_code
        == 404
    )
    as_auditor(client)
    assert (
        client.post(f"{path}/confirm", json={"contentSha256": final["contentSha256"]}).status_code
        == 403
    )
    assert client.get(path).status_code == 403
    with factory() as db:
        assert db.get(Engagement, ids["engagement_a"]).report_confirmed_at is None


def test_stage_pipeline_walks_dispatch_to_review(backend):  # noqa: F811
    client, factory, ids, *_ = backend
    with factory() as db:
        db.get(Engagement, ids["engagement_a"]).status = EngagementStatus.DRAFT
        db.commit()
    as_auditor(client)
    stage = lambda: client.get(f"{base(ids)}/progress").json()["stage"]  # noqa: E731
    seen = [stage()]
    client.post(f"{base(ids)}/checklist/send")
    seen.append(stage())
    as_client(client)
    upload(client, ids, "doc.txt", item="item_a")
    as_auditor(client)
    seen.append(stage())
    as_client(client)
    client.post(f"{base(ids, 'client')}/items/{ids['item_a']}/submit")
    as_auditor(client)
    seen.append(stage())
    client.post(
        f"{base(ids)}/items/{ids['item_a']}/issues",
        json={"kind": "outdated", "documentId": _doc(factory, ids), "note": "Please update."},
    )
    seen.append(stage())
    assert seen == [
        "not_sent", "checklist_sent", "client_working", "under_review", "info_requested",
    ]  # fmt: skip


def _doc(factory, ids):
    with factory() as db:
        return db.scalar(select(Document.id).where(Document.engagement_id == ids["engagement_a"]))


def test_client_workflow_payloads_never_carry_internal_material(backend):  # noqa: F811
    client, factory, ids, *_ = backend
    from tests.test_route_isolation import LEAKS, _seed_internal_material

    _seed_internal_material(factory, ids)
    real_workflow_rows(factory, ids)
    as_client(client)
    for path in (f"{base(ids, 'client')}/progress", f"{base(ids, 'client')}/issues"):
        response = client.get(path)
        assert response.status_code == 200
        assert not set(keys(response.json())) & FORBIDDEN, path
        assert not any(marker in json.dumps(response.json()) for marker in LEAKS)
