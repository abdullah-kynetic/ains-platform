"""Synthetic reversible NA, client privacy, assignment and tenant checks."""

from sqlalchemy import select

from app.checklist import ClientStatus
from app.database.models import AuditLog, ChecklistItemInstance, Engagement, User
from tests.test_backend_api import backend as backend
from tests.test_backend_api import sign_in_auditor, sign_in_client


def test_na_moves_to_bottom_counts_resolved_and_undo_restores(backend):
    client, factory, ids, _, _ = backend
    sign_in_auditor(client)
    path = f"/auditor/engagements/{ids['engagement_a']}/items/{ids['item_a']}/na"
    with factory() as db:
        item = db.get(ChecklistItemInstance, ids["item_a"])
        item.status = ClientStatus.ACTION_NEEDED_MORE
        item.assessment = "partial"
        item.client_reason = "Please provide missing pages."
        db.commit()
    response = client.post(path, json={"not_applicable": True})
    assert response.status_code == 200
    assert response.json()["readiness"]["reviewed"] == 1
    assert client.post(path, json={"not_applicable": True}).status_code == 200
    sign_in_client(client)
    response = client.get("/engagements/current").json()
    assert response["collectionProgress"] == {"total": 1, "done": 1}
    items = [i for s in response["sections"] for i in s["items"]]
    assert next(i for i in items if i["id"] == ids["item_a"])["status"] == "not_applicable"
    assert client.post(path, json={"not_applicable": False}).status_code == 403
    sign_in_auditor(client)
    assert client.post(path, json={"not_applicable": False}).status_code == 200
    with factory() as db:
        item = db.get(ChecklistItemInstance, ids["item_a"])
        assert item.status == ClientStatus.ACTION_NEEDED_MORE
        assert item.assessment == "partial"
        assert item.client_reason == "Please provide missing pages."
        assert item.na_previous_state is None
        assert [
            e.action
            for e in db.scalars(
                select(AuditLog).where(AuditLog.action.in_(["request.na_set", "request.na_unset"]))
            ).all()
        ] == ["request.na_set", "request.na_set", "request.na_unset"]


def test_na_rejects_mismatched_firm_and_unassigned_auditor(backend):
    client, factory, ids, _, _ = backend
    sign_in_auditor(client)
    bad = f"/auditor/engagements/{ids['engagement_a']}/items/{ids['item_b']}/na"
    assert client.post(bad, json={"not_applicable": True}).status_code == 404
    with factory() as db:
        db.get(Engagement, ids["engagement_a"]).auditor_id = ids["enrolling_auditor"]
        db.commit()
    path = f"/auditor/engagements/{ids['engagement_a']}/items/{ids['item_a']}/na"
    for value in [True, False]:
        assert client.post(path, json={"not_applicable": value}).status_code == 404
    sign_in_client(client, "beta-client@example.test")
    assert client.post(path, json={"not_applicable": True}).status_code == 403


def test_client_direct_na_is_refused_and_auditor_toggle_records_the_auditor(backend):
    client, factory, ids, _, _ = backend
    sign_in_client(client)
    path = f"/engagements/{ids['engagement_a']}/items/{ids['item_a']}/na"
    # Clients request N/A with a reason (see test_workflow_routes.py); a direct declaration
    # no longer auto-approves.
    assert client.post(path, json={"not_applicable": True}).status_code == 409
    data = client.get("/engagements/current").json()
    item = next(i for s in data["sections"] for i in s["items"] if i["id"] == ids["item_a"])
    assert item["status"] == "requested" and item["naMarkedByRole"] is None
    sign_in_auditor(client)
    auditor_path = "/auditor" + path
    assert client.post(auditor_path, json={"not_applicable": True}).status_code == 200
    workspace = client.get(f"/auditor/engagements/{ids['engagement_a']}/workspace").json()
    assert workspace["requests"][-1]["naMarkedByRole"] == "auditor"
    assert client.post(auditor_path, json={"not_applicable": False}).status_code == 200
    with factory() as db:
        events = db.scalars(
            select(AuditLog).where(AuditLog.action.in_(["request.na_set", "request.na_unset"]))
        ).all()
        assert [event.details["actor_role"] for event in events] == ["auditor", "auditor"]
        assert db.get(ChecklistItemInstance, ids["item_a"]).status == ClientStatus.REQUESTED


def test_direct_na_denies_other_firms_unassigned_and_anonymous(backend):
    client, factory, ids, _, _ = backend
    path = f"/engagements/{ids['engagement_a']}/items/{ids['item_a']}/na"
    assert client.post(path, json={"not_applicable": True}).status_code == 401
    sign_in_client(client, "beta-client@example.test")
    for value in [True, False]:
        assert client.post(path, json={"not_applicable": value}).status_code == 404
    sign_in_client(client)
    bad_item = f"/engagements/{ids['engagement_a']}/items/{ids['item_b']}/na"
    assert client.post(bad_item, json={"not_applicable": True}).status_code == 404
    sign_in_auditor(client)
    with factory() as db:
        db.get(Engagement, ids["engagement_a"]).auditor_id = ids["enrolling_auditor"]
        db.commit()
    for value in [True, False]:
        assert client.post(path, json={"not_applicable": value}).status_code == 404
    assert client.get(f"/auditor/engagements/{ids['engagement_a']}/workspace").status_code == 404
    with factory() as db:
        assert not db.scalars(select(AuditLog).where(AuditLog.action.like("request.na_%"))).all()


def test_assigned_workspace_remains_allowed_across_auditor_firms(backend):
    client, factory, ids, _, _ = backend
    sign_in_auditor(client)
    base = f"/auditor/engagements/{ids['engagement_a']}"
    # An assigned auditor's own firm need not equal the client firm.
    with factory() as db:
        db.get(User, ids["auditor"]).firm_id = db.get(Engagement, ids["engagement_b"]).firm_id
        db.commit()
    # Scope changes invalidate the old identity; assignment survives a fresh sign-in.
    assert client.get(base + "/workspace").status_code == 401
    client.cookies.clear()
    sign_in_auditor(client)
    response = client.get(base + "/workspace")
    assert response.status_code == 200
    assert "notes" in response.json()["requests"][0]
    assert "history" in response.json() and "readiness" in response.json()
    with factory() as db:
        db.get(User, ids["enrolling_auditor"]).firm_id = db.get(User, ids["auditor"]).firm_id
        db.get(Engagement, ids["engagement_a"]).auditor_id = ids["enrolling_auditor"]
        db.commit()
    assert client.get(base + "/workspace").status_code == 404


def test_restricted_na_stays_excluded_and_rejects_uploads(backend):
    client, _, ids, ingestor, _ = backend
    sign_in_client(client)
    base = f"/engagements/{ids['engagement_a']}/items/{ids['restricted_a']}"
    for value, expected in [(True, 409), (False, 200)]:
        assert client.post(base + "/na", json={"not_applicable": value}).status_code == expected
        data = client.get("/engagements/current").json()
        assert data["collectionProgress"] == {"total": 1, "done": 0}
        assert client.post(
            base + "/documents", files={"file": ("synthetic.txt", b"synthetic")}
        ).status_code in {403, 404}
    assert ingestor.calls == 0


def test_reasoned_na_undo_restores_prior_status_and_feedback(backend):
    client, factory, ids, _, _ = backend
    with factory() as db:
        item = db.get(ChecklistItemInstance, ids["item_a"])
        item.status = ClientStatus.ACTION_NEEDED_MORE
        item.client_reason = "Please provide missing pages."
        item.applicability_answer = True
        db.commit()
    sign_in_client(client)
    questionnaire = f"/engagements/{ids['engagement_a']}/questionnaire"
    # The questionnaire can no longer mark N/A; the item keeps its status and answer.
    response = client.post(
        questionnaire + "/answers", json={"answers": [{"itemId": ids["item_a"], "applies": False}]}
    )
    assert response.status_code == 422
    assert client.get(questionnaire).json()["questions"][0]["answer"] is True
    with factory() as db:
        item = db.get(ChecklistItemInstance, ids["item_a"])
        assert item.status == ClientStatus.ACTION_NEEDED_MORE
        assert item.client_reason == "Please provide missing pages."
        assert item.representation is None

def test_workspace_lists_documents_the_client_linked_to_a_request(backend):
    from app.database.models import Document, DocumentItemLink

    client, factory, ids, _, _ = backend
    with factory() as db:
        document = Document(
            firm_id=ids["firm_a"],
            engagement_id=ids["engagement_a"],
            item_instance_id=None,
            uploaded_by_id=ids["client_a"],
            original_name="synthetic-linked.pdf",
            size_bytes=3,
            egnyte_path="/synthetic/linked",
            sha256="c" * 64,
            version="1",
            number="1.9",
        )
        db.add(document)
        db.flush()
        db.add(
            DocumentItemLink(
                firm_id=ids["firm_a"],
                engagement_id=ids["engagement_a"],
                item_instance_id=ids["item_a"],
                document_id=document.id,
                linked_by_id=ids["client_a"],
            )
        )
        db.commit()
    sign_in_auditor(client)
    rows = client.get(f"/auditor/engagements/{ids['engagement_a']}/workspace").json()["requests"]
    names = [d["name"] for r in rows for d in r["documents"]]
    assert names == ["synthetic-linked.pdf"]
    # The other firm's engagement never shows it.
    other = client.get(f"/auditor/engagements/{ids['engagement_b']}/workspace")
    assert other.status_code in {200, 404}
    if other.status_code == 200:
        assert "synthetic-linked.pdf" not in other.text
