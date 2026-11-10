"""L2-6b: the auditor's per-request test conclusion. Human-entered, never derived."""

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, select

from app.checklist import ClientStatus
from app.database.models import AuditLog, Base, ChecklistItemInstance, Engagement
from tests.test_backend_api import backend, sign_in_auditor, sign_in_client  # noqa: F401


def _url(ids, request_id=""):
    base = f"/auditor/engagements/{ids['engagement_a']}/checklist-tests"
    return f"{base}/{request_id}" if request_id else base


def test_list_set_clear_and_audit(backend):  # noqa: F811
    client, factory, ids, *_ = backend
    sign_in_auditor(client)
    rows = client.get(_url(ids)).json()
    assert rows and set(rows[0]) == {
        "requestId",
        "title",
        "section",
        "restricted",
        "conclusion",
        "updatedAt",
    }
    assert all(row["conclusion"] is None and row["updatedAt"] is None for row in rows)
    first = rows[0]["requestId"]
    done = client.patch(_url(ids, first), json={"conclusion": "partial"})
    assert done.status_code == 200
    row = next(r for r in done.json() if r["requestId"] == first)
    assert row["conclusion"] == "partial" and row["updatedAt"] is not None
    cleared = client.patch(_url(ids, first), json={"conclusion": None}).json()
    assert next(r for r in cleared if r["requestId"] == first)["conclusion"] is None
    with factory() as db:
        logs = list(
            db.scalars(select(AuditLog).where(AuditLog.action == "checklist.conclusion_set"))
        )
    assert [(log.details["from"], log.details["to"]) for log in logs] == [
        (None, "partial"),
        ("partial", None),
    ]
    assert {log.firm_id for log in logs} == {ids["firm_a"]}


def test_invalid_unknown_and_extra_fields_are_rejected(backend):  # noqa: F811
    client, _factory, ids, *_ = backend
    sign_in_auditor(client)
    first = client.get(_url(ids)).json()[0]["requestId"]
    assert client.patch(_url(ids, first), json={"conclusion": "accepted"}).status_code == 422
    assert client.patch(_url(ids, first), json={}).status_code == 422
    assert client.patch(_url(ids, first), json={"conclusion": "pass", "x": 1}).status_code == 422
    assert client.patch(_url(ids, "AML-BD-999"), json={"conclusion": "pass"}).status_code == 404


def test_not_applicable_rows_sort_last_and_keep_their_ids(backend):  # noqa: F811
    client, factory, ids, *_ = backend
    sign_in_auditor(client)
    order = [r["requestId"] for r in client.get(_url(ids)).json()]
    assert len(order) > 1
    lead = order[0]
    by_conclusion = client.patch(_url(ids, lead), json={"conclusion": "na"}).json()
    assert [r["requestId"] for r in by_conclusion] == order[1:] + [lead]
    client.patch(_url(ids, lead), json={"conclusion": None})
    with factory() as db:  # an item the client's N/A request was accepted for also sorts last
        item = db.scalar(
            select(ChecklistItemInstance).where(
                ChecklistItemInstance.engagement_id == ids["engagement_a"],
                ChecklistItemInstance.item_key == lead,
            )
        )
        item.status = ClientStatus.NOT_APPLICABLE
        db.commit()
    by_state = [r["requestId"] for r in client.get(_url(ids)).json()]
    assert by_state == order[1:] + [lead]


def test_clients_cannot_reach_it_and_do_not_see_conclusions(backend):  # noqa: F811
    client, _factory, ids, *_ = backend
    sign_in_auditor(client)
    first = client.get(_url(ids)).json()[0]["requestId"]
    client.patch(_url(ids, first), json={"conclusion": "fail"})
    client.cookies.clear()
    sign_in_client(client)
    assert client.get(_url(ids)).status_code == 403
    assert client.patch(_url(ids, first), json={"conclusion": "pass"}).status_code == 403
    for path in (
        "/engagements/current",
        f"/engagements/{ids['engagement_a']}/progress",
        f"/engagements/{ids['engagement_a']}/questionnaire",
    ):
        assert "conclusion" not in client.get(path).text.casefold(), path


def test_unassigned_auditor_and_other_engagements_items_are_not_found(backend):  # noqa: F811
    client, factory, ids, *_ = backend
    sign_in_auditor(client)
    with factory() as db:
        other = db.scalar(
            select(ChecklistItemInstance).where(
                ChecklistItemInstance.engagement_id == ids["engagement_b"]
            )
        )
        a_keys = set(
            db.scalars(
                select(ChecklistItemInstance.item_key).where(
                    ChecklistItemInstance.engagement_id == ids["engagement_a"]
                )
            )
        )
    if other is not None and other.item_key not in a_keys:
        assert (
            client.patch(_url(ids, other.item_key), json={"conclusion": "pass"}).status_code == 404
        )
    with factory() as db:
        db.get(Engagement, ids["engagement_a"]).auditor_id = None
        db.commit()
    assert client.get(_url(ids)).status_code == 404
    assert client.patch(_url(ids, "AML-BD-004"), json={"conclusion": "pass"}).status_code == 404


def test_conclusion_migration_up_down_and_idempotent():
    config = Config("alembic.ini")
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with engine.begin() as connection:
        config.attributes["connection"] = connection
        command.stamp(config, "a122_checklist_conclusions")
        command.downgrade(config, "a121_practice_routes")
        columns = {c["name"] for c in inspect(connection).get_columns("checklist_item_instances")}
        assert "conclusion" not in columns
        command.upgrade(config, "a122_checklist_conclusions")
        columns = {c["name"] for c in inspect(connection).get_columns("checklist_item_instances")}
        assert {"conclusion", "conclusion_updated_at", "conclusion_updated_by_id"} <= columns
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with engine.begin() as connection:  # schema built from the models, then migrated over
        config.attributes["connection"] = connection
        command.stamp(config, "a121_practice_routes")
        command.upgrade(config, "a122_checklist_conclusions")
    engine.dispose()
