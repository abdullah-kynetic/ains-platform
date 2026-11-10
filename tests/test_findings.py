"""L2-6d: findings (auditor-only) and the response requests a client sees. Synthetic data only."""

import json

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, select

from app.database.models import (
    AuditLog,
    Base,
    Document,
    Engagement,
    Finding,
    ResponseRequest,
)
from tests.test_backend_api import backend, sign_in_auditor, sign_in_client  # noqa: F401

SECRET_TEXT = {
    "title": "FINDING-INTERNAL-TITLE",
    "rule": "FINDING-INTERNAL-RULE",
    "condition": "FINDING-INTERNAL-CONDITION",
    "cause": "FINDING-INTERNAL-CAUSE",
    "effect": "FINDING-INTERNAL-EFFECT",
    "recommendation": "FINDING-INTERNAL-RECOMMENDATION",
}


def _url(ids, tail=""):
    return f"/auditor/engagements/{ids['engagement_a']}/findings{tail}"


def _document(factory, ids, name="alerts-log.xlsx") -> None:
    with factory() as db:
        db.add(
            Document(
                firm_id=ids["firm_a"],
                engagement_id=ids["engagement_a"],
                uploaded_by_id=ids["client_a"],
                original_name=name,
                size_bytes=1,
                egnyte_path="/synthetic/f",
                sha256="d" * 64,
                version="1",
                number="1.40",
            )
        )
        db.commit()


def _body(**over):
    return {
        **SECRET_TEXT,
        "severity": "high",
        "citations": [{"document": "alerts-log.xlsx", "page": 3}],
        **over,
    }


def _issue(client, factory, ids) -> tuple[str, str]:
    """Draft, approve and release one finding; returns (finding id, response request id)."""
    _document(factory, ids)
    finding = client.post(_url(ids), json=_body()).json()
    fid = finding["id"]
    assert (
        client.post(f"/auditor/findings/{fid}/status", json={"status": "approved"}).status_code
        == 200
    )
    released = client.post(
        f"/auditor/findings/{fid}/response-request",
        json={"title": "Alert closures", "requestText": "Please describe how alerts are closed."},
    )
    assert released.status_code == 201 and released.json()["status"] == "issued"
    with factory() as db:
        rid = db.scalar(select(ResponseRequest.id).where(ResponseRequest.finding_id == fid))
    return fid, rid


def test_finding_lifecycle_with_server_enforced_rules(backend):  # noqa: F811
    client, factory, ids, *_ = backend
    sign_in_auditor(client)
    assert client.get(_url(ids)).json() == []
    empty = client.post(_url(ids), json={}).json()
    assert empty["status"] == "draft" and empty["severity"] == "moderate"
    approve = f"/auditor/findings/{empty['id']}/status"
    assert client.post(approve, json={"status": "approved"}).status_code == 422  # fields missing
    full = client.put(_url(ids, f"/{empty['id']}"), json=_body(citations=[])).json()
    assert client.post(approve, json={"status": "approved"}).json()["detail"].startswith("Cite")
    client.put(_url(ids, f"/{empty['id']}"), json=_body())
    # The cited document must be a real document of this engagement.
    assert (
        "not a document of this engagement"
        in client.post(approve, json={"status": "approved"}).json()["detail"]
    )
    _document(factory, ids)
    approved = client.post(approve, json={"status": "approved"})
    assert approved.status_code == 200 and approved.json()["status"] == "approved"
    assert set(approved.json()) == {
        "id",
        "engagementId",
        "title",
        "rule",
        "condition",
        "cause",
        "effect",
        "recommendation",
        "severity",
        "citations",
        "managementResponse",
        "respondedAt",
        "status",
        "updatedAt",
    }
    # Editing an approved finding returns it to draft.
    edited = client.put(_url(ids, f"/{empty['id']}"), json=_body(severity="low")).json()
    assert edited["status"] == "draft" and edited["severity"] == "low"
    assert full["status"] == "draft"
    # Bad moves and bad values.
    assert client.post(approve, json={"status": "closed"}).status_code == 409
    assert client.post(approve, json={"status": "issued"}).status_code == 409
    assert client.post(approve, json={"status": "responded"}).status_code == 409
    assert client.post(approve, json={"status": "nope"}).status_code == 422
    assert (
        client.put(_url(ids, f"/{empty['id']}"), json=_body(severity="urgent")).status_code == 422
    )
    assert (
        client.put(
            _url(ids, f"/{empty['id']}"), json=_body(citations=[{"document": "a", "page": 0}])
        ).status_code
        == 422
    )
    assert client.put(_url(ids, "/missing"), json=_body()).status_code == 404
    assert client.delete(f"/auditor/findings/{empty['id']}").status_code == 204
    assert client.get(_url(ids)).json() == []
    with factory() as db:
        actions = set(db.scalars(select(AuditLog.action)))
        assert {
            "finding.drafted",
            "finding.edited",
            "finding.status_changed",
            "finding.deleted",
        } <= actions


def test_release_makes_a_client_request_without_any_finding_field(backend):  # noqa: F811
    client, factory, ids, *_ = backend
    sign_in_auditor(client)
    _document(factory, ids)
    draft = client.post(_url(ids), json=_body()).json()
    release = f"/auditor/findings/{draft['id']}/response-request"
    ask = {"title": "Alert closures", "requestText": "Please describe how alerts are closed."}
    assert client.post(release, json=ask).status_code == 409  # not approved yet
    assert (
        client.post(
            f"/auditor/findings/{draft['id']}/status", json={"status": "approved"}
        ).status_code
        == 200
    )
    assert client.post(release, json={"title": " ", "requestText": "x"}).status_code == 422
    client.cookies.clear()
    sign_in_client(client)
    url = f"/engagements/{ids['engagement_a']}/response-requests"
    assert client.get(url).json() == []  # approved is not released
    client.cookies.clear()
    sign_in_auditor(client)
    assert client.post(release, json=ask).status_code == 201
    assert client.post(release, json=ask).status_code == 409  # one release per finding
    client.cookies.clear()
    sign_in_client(client)
    seen = client.get(url)
    rows = seen.json()
    assert len(rows) == 1
    assert set(rows[0]) == {
        "id",
        "title",
        "requestText",
        "status",
        "response",
        "respondedAt",
        "releasedAt",
    }
    assert rows[0]["title"] == "Alert closures" and rows[0]["status"] == "open"
    text = json.dumps(rows) + seen.text
    assert not any(value in text for value in SECRET_TEXT.values())
    assert (
        draft["id"] not in text and "alerts-log.xlsx" not in text and "high" not in text.casefold()
    )


def test_client_reply_moves_the_finding_to_responded_once(backend):  # noqa: F811
    client, factory, ids, *_ = backend
    sign_in_auditor(client)
    fid, rid = _issue(client, factory, ids)
    assert client.put(_url(ids, f"/{fid}"), json=_body()).status_code == 409  # issued: no edits
    assert client.delete(f"/auditor/findings/{fid}").status_code == 409
    client.cookies.clear()
    sign_in_client(client)
    reply = f"/engagements/{ids['engagement_a']}/response-requests/{rid}/response"
    assert client.post(reply, json={"text": "  "}).status_code == 422
    assert client.post(reply, json={"text": "x" * 4001}).status_code == 422
    done = client.post(reply, json={"text": "We agree and will document closures."})
    assert done.status_code == 200
    row = done.json()[0]
    assert row["status"] == "responded" and row["response"].startswith("We agree")
    assert row["respondedAt"] is not None
    assert client.post(reply, json={"text": "again"}).status_code == 409
    assert (
        client.post(
            f"/engagements/{ids['engagement_a']}/response-requests/nope/response",
            json={"text": "x"},
        ).status_code
        == 404
    )
    client.cookies.clear()
    sign_in_auditor(client)
    finding = client.get(_url(ids)).json()[0]
    assert finding["status"] == "responded" and finding["managementResponse"].startswith("We agree")
    assert (
        client.post(f"/auditor/findings/{fid}/status", json={"status": "closed"}).json()["status"]
        == "closed"
    )
    assert (
        client.post(f"/auditor/findings/{fid}/status", json={"status": "draft"}).status_code == 409
    )
    with factory() as db:
        logs = list(db.scalars(select(AuditLog).where(AuditLog.action.like("%response%"))))
    assert {log.action for log in logs} == {
        "finding.response_released",
        "response_request.responded",
    }
    assert all("text_length" in log.details and "text" not in log.details for log in logs)
    assert {log.firm_id for log in logs} == {ids["firm_a"]}


def test_other_firms_and_unassigned_auditors_cannot_reach_findings(backend):  # noqa: F811
    client, factory, ids, *_ = backend
    sign_in_auditor(client)
    fid, rid = _issue(client, factory, ids)
    with factory() as db:  # a request that belongs to firm B's engagement
        other = Finding(
            firm_id=ids["firm_b"],
            engagement_id=ids["engagement_b"],
            created_by_id=ids["auditor"],
            status="issued",
        )
        db.add(other)
        db.flush()
        foreign = ResponseRequest(
            firm_id=ids["firm_b"],
            engagement_id=ids["engagement_b"],
            finding_id=other.id,
            title="B",
            request_text="B",
            released_by_id=ids["auditor"],
        )
        db.add(foreign)
        db.commit()
        foreign_id = foreign.id
    client.cookies.clear()
    sign_in_client(client)  # firm A's client
    mine = f"/engagements/{ids['engagement_a']}"
    assert (
        client.post(
            f"{mine}/response-requests/{foreign_id}/response", json={"text": "x"}
        ).status_code
        == 404
    )
    assert client.get(f"/engagements/{ids['engagement_b']}/response-requests").status_code in {
        403,
        404,
    }
    assert [r["title"] for r in client.get(f"{mine}/response-requests").json()] == [
        "Alert closures"
    ]
    assert client.get(_url(ids)).status_code == 403
    client.cookies.clear()
    sign_in_auditor(client)
    with factory() as db:
        db.get(Engagement, ids["engagement_a"]).auditor_id = None
        db.commit()
    assert client.get(_url(ids)).status_code == 404
    assert (
        client.post(f"/auditor/findings/{fid}/status", json={"status": "closed"}).status_code == 404
    )
    assert client.delete(f"/auditor/findings/{fid}").status_code == 404
    assert (
        client.post(
            f"/auditor/findings/{fid}/response-request", json={"title": "t", "requestText": "r"}
        ).status_code
        == 404
    )
    with factory() as db:
        assert db.get(ResponseRequest, rid).status == "open"


def test_findings_migration_up_down_and_idempotent():
    config = Config("alembic.ini")
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with engine.begin() as connection:
        config.attributes["connection"] = connection
        command.stamp(config, "a124_findings_responses")
        command.downgrade(config, "a123_workpapers_samples")
        assert not {"findings", "response_requests"} & set(inspect(connection).get_table_names())
        command.upgrade(config, "a124_findings_responses")
        assert {"findings", "response_requests"} <= set(inspect(connection).get_table_names())
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with engine.begin() as connection:
        config.attributes["connection"] = connection
        command.stamp(config, "a123_workpapers_samples")
        command.upgrade(config, "a124_findings_responses")
    engine.dispose()
