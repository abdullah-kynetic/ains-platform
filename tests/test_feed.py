"""L2-6g: engagement activity, derived notifications with read marks, and search."""

from datetime import UTC, date, datetime, timedelta

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, select

from app.database.models import Base, Document, Engagement, Firm, NotificationRead
from tests.test_backend_api import backend, sign_in_auditor  # noqa: F401
from tests.test_workpapers_samples import REQUEST, _document, _sign_in, _teammates


def _setup(backend):  # noqa: F811
    client, factory, ids, *_ = backend
    _teammates(factory, ids)
    return client, factory, ids


def test_activity_lists_action_names_for_this_engagement_only(backend):  # noqa: F811
    client, factory, ids = _setup(backend)
    sign_in_auditor(client)
    doc = _document(factory, ids)
    body = {"procedure": "SECRET PROCEDURE TEXT", "evidenceIds": [doc], "conclusion": "pass"}
    assert client.put(f"/auditor/engagements/{ids['engagement_a']}/workpapers/{REQUEST}", json=body)
    feed = client.get(f"/auditor/engagements/{ids['engagement_a']}/activity")
    assert feed.status_code == 200
    rows = feed.json()
    assert rows and set(rows[0]) == {"id", "engagementId", "at", "actor", "action"}
    assert any(r["action"] == "Workpaper saved." for r in rows)
    assert all(r["engagementId"] == ids["engagement_a"] for r in rows)
    assert "SECRET PROCEDURE TEXT" not in feed.text
    other = client.get(f"/auditor/engagements/{ids['engagement_b']}/activity")
    assert "Workpaper saved." not in other.text
    _sign_in(client, "colleague-a@example.test")
    assert client.get(f"/auditor/engagements/{ids['engagement_a']}/activity").status_code == 404


def test_notifications_are_derived_scoped_and_read_marks_are_per_user(backend):  # noqa: F811
    client, factory, ids = _setup(backend)
    _document(factory, ids)
    with factory() as db:
        db.get(Engagement, ids["engagement_a"]).due_date = date.today() - timedelta(days=2)
        db.get(Document, db.scalar(select(Document.id))).created_at = datetime.now(UTC)
        db.commit()
    sign_in_auditor(client)
    items = client.get("/auditor/notifications").json()
    kinds = {n["kind"] for n in items}
    assert "deadline" in kinds and "upload" in kinds
    assert set(items[0]) == {"id", "at", "title", "detail", "href", "kind", "read"}
    assert all(n["read"] is False for n in items)
    deadline = next(n for n in items if n["kind"] == "deadline")
    assert "2 days overdue" in deadline["title"]
    assert client.post(f"/auditor/notifications/{deadline['id']}/read").status_code == 204
    after = {n["id"]: n["read"] for n in client.get("/auditor/notifications").json()}
    assert after[deadline["id"]] is True and not all(after.values())
    assert client.post("/auditor/notifications/nope/read").status_code == 404
    assert client.post("/auditor/notifications/read-all").status_code == 204
    assert all(n["read"] for n in client.get("/auditor/notifications").json())
    with factory() as db:
        rows = db.scalars(select(NotificationRead)).all()
        assert {r.user_id for r in rows} == {ids["auditor"]}
    # An unassigned colleague sees none of it and cannot mark it.
    _sign_in(client, "colleague-a@example.test")
    assert client.get("/auditor/notifications").json() == []
    assert client.post(f"/auditor/notifications/{deadline['id']}/read").status_code == 404


def test_search_is_scoped_literal_and_returns_links(backend):  # noqa: F811
    client, factory, ids = _setup(backend)
    _document(factory, ids)
    with factory() as db:
        firm = db.get(Firm, ids["firm_a"]).name
    sign_in_auditor(client)
    hits = client.get("/auditor/search", params={"q": firm[:6]}).json()
    assert {"Client", "Engagement"} <= {h["kind"] for h in hits}
    assert set(hits[0]) == {"id", "kind", "title", "detail", "href"}
    docs = client.get("/auditor/search", params={"q": "synthetic-evid"}).json()
    assert [h["kind"] for h in docs] == ["Document"]
    assert docs[0]["href"].endswith("/documents")
    assert client.get("/auditor/search", params={"q": "AML-BD-004"}).json()[0]["kind"] == "Request"
    assert client.get("/auditor/search").json() == []
    assert client.get("/auditor/search", params={"q": "%"}).json() == []
    assert client.get("/auditor/search", params={"q": "_"}).json() == []
    assert client.get("/auditor/search", params={"q": "x" * 101}).status_code == 422
    _sign_in(client, "colleague-a@example.test")
    assert client.get("/auditor/search", params={"q": firm[:6]}).json() == []


def test_notification_reads_migration_up_down_and_idempotent():
    config = Config("alembic.ini")
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with engine.begin() as connection:
        config.attributes["connection"] = connection
        command.stamp(config, "a127_notification_reads")
        command.downgrade(config, "a126_engagement_signoffs")
        assert "notification_reads" not in set(inspect(connection).get_table_names())
        command.upgrade(config, "a127_notification_reads")
        assert "notification_reads" in set(inspect(connection).get_table_names())
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with engine.begin() as connection:
        config.attributes["connection"] = connection
        command.stamp(config, "a126_engagement_signoffs")
        command.upgrade(config, "a127_notification_reads")
    engine.dispose()
