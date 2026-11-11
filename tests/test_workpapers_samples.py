"""L2-6c: workpapers (prepare, independent review) and sample sets. Auditor-only."""

from datetime import UTC, datetime

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, select

from app.auth.security import hash_password
from app.database.models import AuditLog, Base, Document, Practice, SampleItem, User, UserRole
from tests.test_backend_api import (
    AUDITOR_PASSWORD,
    backend,  # noqa: F401
    sign_in_auditor,
    sign_in_client,
)

REQUEST = "AML-BD-004"  # the fixture's item in firm A, engagement A


def _wp(ids, request_id=""):
    base = f"/auditor/engagements/{ids['engagement_a']}/workpapers"
    return f"{base}/{request_id}" if request_id else base


def _samples(ids):
    return f"/auditor/engagements/{ids['engagement_a']}/samples"


def _document(factory, ids, engagement="engagement_a", firm="firm_a") -> str:
    with factory() as db:
        document = Document(
            firm_id=ids[firm],
            engagement_id=ids[engagement],
            uploaded_by_id=ids["client_a"],
            original_name="synthetic-evidence.txt",
            size_bytes=1,
            egnyte_path=f"/synthetic/{engagement}",
            sha256="c" * 64,
            version="1",
        )
        db.add(document)
        db.commit()
        return document.id


def _teammates(factory, ids) -> None:
    """The fixture auditor (assigned to both engagements) is in practice A with a reviewer, a
    plain colleague, and a reviewer from an unrelated practice B."""
    with factory() as db:
        a, b = Practice(name="Synthetic A"), Practice(name="Synthetic B")
        db.add_all([a, b])
        db.flush()
        db.get(User, ids["auditor"]).practice_id = a.id
        for email, practice, role in (
            ("reviewer-a@example.test", a, "reviewer"),
            ("colleague-a@example.test", a, "auditor"),
            ("reviewer-b@example.test", b, "reviewer"),
        ):
            db.add(
                User(
                    email=email,
                    name=email.split("@")[0],
                    role=UserRole.AUDITOR,
                    password_hash=hash_password(AUDITOR_PASSWORD),
                    accepted_at=datetime.now(UTC),
                    practice_id=practice.id,
                    team_role=role,
                )
            )
        db.commit()


def _sign_in(client, email: str) -> None:
    client.cookies.clear()
    response = client.post(
        "/auth/password",
        json={
            "email": email,
            "password": AUDITOR_PASSWORD,
        },
    )
    assert response.status_code == 200, response.text


def test_workpaper_save_shape_evidence_and_audit(backend):  # noqa: F811
    client, factory, ids, *_ = backend
    sign_in_auditor(client)
    assert client.get(_wp(ids)).json() == []
    doc = _document(factory, ids)
    body = {
        "requestId": REQUEST,
        "procedure": "Read the program.",
        "evidenceIds": [doc, doc],
        "conclusion": "partial",
    }
    saved = client.put(_wp(ids, REQUEST), json=body)
    assert saved.status_code == 200
    wp = saved.json()
    assert set(wp) == {
        "requestId",
        "procedure",
        "evidenceIds",
        "conclusion",
        "preparer",
        "preparedAt",
        "reviewer",
        "reviewedAt",
    }
    assert wp["evidenceIds"] == [doc] and wp["preparer"] == "Synthetic Auditor"
    assert wp["reviewer"] == "" and wp["reviewedAt"] is None and wp["conclusion"] == "partial"
    assert [w["requestId"] for w in client.get(_wp(ids)).json()] == [REQUEST]
    with factory() as db:
        log = db.scalar(select(AuditLog).where(AuditLog.action == "workpaper.saved"))
        assert log.firm_id == ids["firm_a"] and log.details["request_id"] == REQUEST


def test_workpaper_validation_and_foreign_evidence(backend):  # noqa: F811
    client, factory, ids, *_ = backend
    sign_in_auditor(client)
    base = {"procedure": "p", "evidenceIds": [], "conclusion": None}
    assert client.put(_wp(ids, "AML-BD-999"), json=base).status_code == 404
    assert client.put(_wp(ids, REQUEST), json={**base, "conclusion": "accepted"}).status_code == 422
    assert client.put(_wp(ids, REQUEST), json={**base, "x": 1}).status_code == 422
    assert client.put(_wp(ids, REQUEST), json={**base, "procedure": "x" * 8001}).status_code == 422
    # A real document of another firm's engagement cannot be cited as evidence.
    foreign = _document(factory, ids, engagement="engagement_b", firm="firm_b")
    assert client.put(_wp(ids, REQUEST), json={**base, "evidenceIds": [foreign]}).status_code == 422
    assert client.put(_wp(ids, REQUEST), json={**base, "evidenceIds": ["nope"]}).status_code == 422
    assert client.get(_wp(ids)).json() == []


def test_review_needs_a_different_person_and_edits_clear_it(backend):  # noqa: F811
    client, factory, ids, *_ = backend
    _teammates(factory, ids)
    sign_in_auditor(client)
    body = {"procedure": "Original.", "evidenceIds": [], "conclusion": "pass"}
    assert client.put(_wp(ids, REQUEST), json=body).status_code == 200
    # The preparer cannot review their own work; nothing is recorded.
    assert client.post(f"{_wp(ids, REQUEST)}/review").status_code == 409
    assert client.get(_wp(ids)).json()[0]["reviewedAt"] is None
    _sign_in(client, "reviewer-a@example.test")
    reviewed = client.post(f"{_wp(ids, REQUEST)}/review")
    assert reviewed.status_code == 200
    assert reviewed.json()[0]["reviewer"] == "reviewer-a"
    assert reviewed.json()[0]["reviewedAt"] is not None
    # Same-text re-save keeps the review; a changed procedure or conclusion clears it.
    sign_in_auditor(client)
    assert client.put(_wp(ids, REQUEST), json=body).json()["reviewer"] == "reviewer-a"
    changed = client.put(_wp(ids, REQUEST), json={**body, "conclusion": "fail"}).json()
    assert changed["reviewer"] == "" and changed["reviewedAt"] is None
    with factory() as db:
        actions = [a for a in db.scalars(select(AuditLog.action)) if a.startswith("workpaper.")]
    assert actions.count("workpaper.reviewed") == 1 and "workpaper.saved" in actions
    assert client.post(f"{_wp(ids, 'AML-BD-001')}/review").status_code == 404  # no workpaper


def test_only_same_practice_reviewers_can_see_and_review_unassigned_work(backend):  # noqa: F811
    client, factory, ids, *_ = backend
    _teammates(factory, ids)
    sign_in_auditor(client)
    client.put(_wp(ids, REQUEST), json={"procedure": "p", "evidenceIds": [], "conclusion": None})
    _sign_in(client, "reviewer-a@example.test")
    assert len(client.get(_wp(ids)).json()) == 1
    # Reviewers read and review; they do not prepare or touch samples.
    assert (
        client.put(_wp(ids, REQUEST), json={"procedure": "x", "evidenceIds": []}).status_code == 404
    )
    assert client.get(_samples(ids)).status_code == 404
    for email in ("colleague-a@example.test", "reviewer-b@example.test"):
        _sign_in(client, email)
        assert client.get(_wp(ids)).status_code == 404, email
        assert client.post(f"{_wp(ids, REQUEST)}/review").status_code == 404, email
    with factory() as db:
        assert db.scalar(select(AuditLog.id).where(AuditLog.action == "workpaper.reviewed")) is None


def test_samples_create_record_results_and_audit(backend):  # noqa: F811
    client, factory, ids, *_ = backend
    sign_in_auditor(client)
    assert client.get(_samples(ids)).json() == []
    body = {
        "area": " Wires ",
        "requestId": REQUEST,
        "population": 40,
        "sampleSize": 3,
        "method": "Judgmental",
    }
    created = client.post(_samples(ids), json=body)
    assert created.status_code == 201
    sample = created.json()
    assert set(sample) == {
        "id",
        "engagementId",
        "area",
        "requestId",
        "population",
        "sampleSize",
        "method",
        "items",
    }
    assert sample["area"] == "Wires" and sample["engagementId"] == ids["engagement_a"]
    assert [i["reference"] for i in sample["items"]] == ["ITEM-001", "ITEM-002", "ITEM-003"]
    assert {i["result"] for i in sample["items"]} == {"pending"}
    item = sample["items"][1]
    url = f"/auditor/samples/{sample['id']}/items/{item['id']}"
    out = client.patch(url, json={"result": "exception", "note": "No approval on file."})
    assert out.status_code == 200
    row = out.json()[0]["items"][1]
    assert (row["result"], row["note"]) == ("exception", "No approval on file.")
    kept = client.patch(url, json={"result": "pass"}).json()[0]["items"][1]
    assert (kept["result"], kept["note"]) == ("pass", "No approval on file.")  # note kept
    assert client.patch(url, json={"result": "tested"}).status_code == 422
    with factory() as db:
        logs = list(db.scalars(select(AuditLog).where(AuditLog.action.like("sample.%"))))
        assert {log.firm_id for log in logs} == {ids["firm_a"]} and len(logs) == 3


def test_sample_validation(backend):  # noqa: F811
    client, _factory, ids, *_ = backend
    sign_in_auditor(client)
    ok = {"area": "A", "requestId": None, "population": 10, "sampleSize": 2, "method": "m"}
    assert client.post(_samples(ids), json={**ok, "sampleSize": 11}).status_code == 422
    assert client.post(_samples(ids), json={**ok, "sampleSize": 0}).status_code == 422
    assert (
        client.post(_samples(ids), json={**ok, "sampleSize": 501, "population": 900}).status_code
        == 422
    )
    assert client.post(_samples(ids), json={**ok, "area": " "}).status_code == 422
    assert client.post(_samples(ids), json={**ok, "requestId": "AML-BD-999"}).status_code == 404
    assert client.post(_samples(ids), json=ok).status_code == 201


def test_sample_items_resolve_only_inside_assigned_engagements(backend):  # noqa: F811
    client, factory, ids, *_ = backend
    sign_in_auditor(client)
    one = client.post(
        _samples(ids), json={"area": "A", "population": 5, "sampleSize": 1, "method": "m"}
    ).json()
    item_id = one["items"][0]["id"]
    with factory() as db:
        from app.database.models import Engagement

        db.get(Engagement, ids["engagement_a"]).auditor_id = None
        db.commit()
    assert client.get(_samples(ids)).status_code == 404
    assert (
        client.patch(
            f"/auditor/samples/{one['id']}/items/{item_id}", json={"result": "pass"}
        ).status_code
        == 404
    )
    assert (
        client.patch("/auditor/samples/nope/items/nope", json={"result": "pass"}).status_code == 404
    )
    with factory() as db:
        assert db.get(SampleItem, item_id).result == "pending"


def test_clients_cannot_reach_workpapers_or_samples(backend):  # noqa: F811
    client, _factory, ids, *_ = backend
    sign_in_client(client)
    for method, url, kw in (
        ("GET", _wp(ids), {}),
        ("PUT", _wp(ids, REQUEST), {"json": {"procedure": "p"}}),
        ("POST", f"{_wp(ids, REQUEST)}/review", {}),
        ("GET", _samples(ids), {}),
        (
            "POST",
            _samples(ids),
            {"json": {"area": "a", "population": 2, "sampleSize": 1, "method": "m"}},
        ),
        ("PATCH", "/auditor/samples/x/items/y", {"json": {"result": "pass"}}),
    ):
        assert client.request(method, url, **kw).status_code == 403, (method, url)


def test_workpaper_and_sample_migration_up_down_and_idempotent():
    config = Config("alembic.ini")
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with engine.begin() as connection:
        config.attributes["connection"] = connection
        command.stamp(config, "a123_workpapers_samples")
        command.downgrade(config, "a122_checklist_conclusions")
        tables = set(inspect(connection).get_table_names())
        assert not {"workpapers", "sample_sets", "sample_items"} & tables
        command.upgrade(config, "a123_workpapers_samples")
        assert {"workpapers", "sample_sets", "sample_items"} <= set(
            inspect(connection).get_table_names()
        )
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with engine.begin() as connection:  # schema built from the models, then migrated over
        config.attributes["connection"] = connection
        command.stamp(config, "a122_checklist_conclusions")
        command.upgrade(config, "a123_workpapers_samples")
    engine.dispose()
