"""Explicit release of "Responses requested": clients see title and request text, nothing else."""

import json

from app.database.models import ChecklistItemInstance, Document
from tests.test_backend_api import backend, sign_in_auditor, sign_in_client  # noqa: F401
from tests.test_route_isolation import LEAKS, _seed_internal_material  # noqa: F401

REQUEST_TEXT = "Please send the 2025 independent test engagement letter."
ALLOWED_REASONS = {
    None,
    "Your auditor has requested this additional document.",
    "The auditor confirmed that this requested item applies.",
    "Please replace this file with a readable copy.",
    "Please replace this file with the requested document.",
    "Please provide a file covering the engagement review period.",
    "Please provide the missing pages or a complete copy.",
}


def release(client, ids, text=REQUEST_TEXT, item="item_a"):
    return client.post(
        f"/auditor/engagements/{ids['engagement_a']}/items/{ids[item]}/response-request",
        json={"text": text},
    )


def read(client, ids):
    return client.get(f"/engagements/{ids['engagement_a']}/responses-requested")


def test_unreleased_items_are_never_returned_even_with_internal_material(backend):  # noqa: F811
    client, factory, ids, *_ = backend
    _seed_internal_material(factory, ids)
    sign_in_client(client)
    response = read(client, ids)
    assert response.status_code == 200
    assert response.json() == {"engagementId": ids["engagement_a"], "items": []}
    assert not any(marker in response.text for marker in LEAKS)


def test_released_item_exposes_only_item_id_title_and_request_text(backend):  # noqa: F811
    client, factory, ids, *_ = backend
    _seed_internal_material(factory, ids)
    sign_in_auditor(client)
    assert release(client, ids).status_code == 200
    client.cookies.clear()
    sign_in_client(client)
    body = read(client, ids).json()
    assert len(body["items"]) == 1
    assert set(body["items"][0]) == {"itemId", "title", "requestText"}
    assert body["items"][0]["requestText"] == REQUEST_TEXT
    assert body["items"][0]["title"] == "Written AML program"
    assert not any(marker in json.dumps(body) for marker in LEAKS)
    assert "Synthetic current program." not in json.dumps(body)  # item description not exposed


def test_withdraw_hides_the_request_again(backend):  # noqa: F811
    client, _, ids, *_ = backend
    sign_in_auditor(client)
    release(client, ids)
    path = f"/auditor/engagements/{ids['engagement_a']}/items/{ids['item_a']}/response-request"
    assert client.post(path + "/withdraw").status_code == 200
    client.cookies.clear()
    sign_in_client(client)
    assert read(client, ids).json()["items"] == []


def test_only_assigned_auditors_can_release_and_clients_cannot(backend):  # noqa: F811
    client, factory, ids, *_ = backend
    sign_in_client(client)
    assert release(client, ids).status_code == 403
    client.cookies.clear()
    sign_in_auditor(client)
    other = f"/auditor/engagements/{ids['engagement_b']}/items/{ids['item_b']}/response-request"
    from app.database.models import Engagement

    with factory() as db:
        db.get(Engagement, ids["engagement_b"]).auditor_id = None
        db.commit()
    assert client.post(other, json={"text": "x"}).status_code == 404


def test_restricted_items_cannot_be_released_or_returned(backend):  # noqa: F811
    client, factory, ids, *_ = backend
    sign_in_auditor(client)
    assert release(client, ids, item="restricted_a").status_code == 409
    with factory() as db:  # even if text were forced into the row, the endpoint filters it
        row = db.get(ChecklistItemInstance, ids["restricted_a"])
        row.response_request_text = "SHOULD-NOT-APPEAR"
        row.response_released_at = row.created_at if hasattr(row, "created_at") else None
        db.commit()
    client.cookies.clear()
    sign_in_client(client)
    assert "SHOULD-NOT-APPEAR" not in read(client, ids).text


def test_other_firm_cannot_read_released_requests(backend):  # noqa: F811
    client, _, ids, *_ = backend
    sign_in_auditor(client)
    release(client, ids)
    client.cookies.clear()
    sign_in_client(client, "beta-client@example.test")
    response = read(client, ids)
    assert response.status_code == 404
    assert REQUEST_TEXT not in response.text


def test_release_text_is_bounded_and_audited_without_the_text(backend):  # noqa: F811
    from app.database.models import AuditLog

    client, factory, ids, *_ = backend
    sign_in_auditor(client)
    assert release(client, ids, text="").status_code == 422
    assert release(client, ids, text="x" * 2001).status_code == 422
    assert release(client, ids).status_code == 200
    with factory() as db:
        log = db.query(AuditLog).filter(AuditLog.action == "request.response_released").one()
        assert REQUEST_TEXT not in json.dumps(log.details)


def test_follow_up_and_reason_never_carry_internal_text(backend):  # noqa: F811
    client, factory, ids, *_ = backend
    _seed_internal_material(factory, ids)
    with factory() as db:
        doc = Document(
            firm_id=ids["firm_a"],
            engagement_id=ids["engagement_a"],
            item_instance_id=ids["item_a"],
            uploaded_by_id=ids["client_a"],
            original_name="synthetic.txt",
            size_bytes=3,
            egnyte_path="/synthetic",
            sha256="d" * 64,
            version="1",
        )
        db.add(doc)
        db.commit()
        doc_id = doc.id
    sign_in_auditor(client)
    base = f"/auditor/engagements/{ids['engagement_a']}/items/{ids['item_a']}"
    assert client.post(base + "/follow-up").status_code == 200
    for code in ("unreadable", "wrong_document", "wrong_period", "missing_pages", "usable"):
        assert (
            client.post(base + "/feedback", json={"code": code, "document_id": doc_id}).status_code
            == 200
        )
        client.cookies.clear()
        sign_in_client(client)
        body = client.get("/engagements/current").json()
        items = [i for s in body["sections"] for i in s["items"]]
        item = next(i for i in items if i["id"] == ids["item_a"])
        assert isinstance(item["followUp"], bool)
        assert item["reason"] in ALLOWED_REASONS
        assert not any(marker in json.dumps(body) for marker in LEAKS)
        client.cookies.clear()
        sign_in_auditor(client)


def _release_in_db(factory, item_id, text):
    from datetime import UTC, datetime

    with factory() as db:
        row = db.get(ChecklistItemInstance, item_id)
        row.response_request_text = text
        row.response_released_at = datetime.now(UTC)
        db.commit()


def test_other_engagements_and_firms_never_leak_into_responses_requested(backend):  # noqa: F811
    """Released items elsewhere must not appear. Dropping the engagement/firm filter fails this."""
    from datetime import date

    from app.database.models import Engagement

    client, factory, ids, *_ = backend
    with factory() as db:  # second engagement in the SAME firm, with its own released item
        other = Engagement(
            firm_id=ids["firm_a"],
            auditor_id=ids["auditor"],
            review_period_start=date(2024, 1, 1),
            review_period_end=date(2024, 12, 31),
        )
        db.add(other)
        db.flush()
        sibling = ChecklistItemInstance(
            firm_id=ids["firm_a"],
            engagement_id=other.id,
            item_key="AML-BD-004",
            section_key="governance",
            section_title="AML program and governance",
            title="SIBLING-ENGAGEMENT-TITLE",
            position=1,
        )
        db.add(sibling)
        db.commit()
        sibling_id = sibling.id
    _release_in_db(factory, sibling_id, "SIBLING-ENGAGEMENT-CANARY")
    _release_in_db(factory, ids["item_b"], "OTHER-FIRM-CANARY")
    sign_in_auditor(client)
    assert release(client, ids).status_code == 200
    client.cookies.clear()
    sign_in_client(client)
    body = read(client, ids)
    assert [i["itemId"] for i in body.json()["items"]] == [ids["item_a"]]
    for canary in ("SIBLING-ENGAGEMENT", "OTHER-FIRM-CANARY"):
        assert canary not in body.text
    foreign = client.get(f"/engagements/{ids['engagement_b']}/responses-requested")
    assert foreign.status_code == 404 and "OTHER-FIRM-CANARY" not in foreign.text


def test_withdraw_clears_the_stored_text_and_release_fields(backend):  # noqa: F811
    client, factory, ids, *_ = backend
    sign_in_auditor(client)
    assert release(client, ids).status_code == 200
    path = f"/auditor/engagements/{ids['engagement_a']}/items/{ids['item_a']}/response-request"
    assert client.post(path + "/withdraw").status_code == 200
    with factory() as db:
        row = db.get(ChecklistItemInstance, ids["item_a"])
        assert row.response_request_text is None
        assert row.response_released_at is None
        assert row.response_released_by_id is None
