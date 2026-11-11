"""L2-6f: independence, reviewer approval, partner signature, completion, client signed report."""

import hashlib
from datetime import UTC, datetime

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, select

from app.auth.security import hash_password
from app.database.models import (
    AuditLog,
    Base,
    ChecklistItemInstance,
    Engagement,
    EngagementSignoff,
    Finding,
    User,
    UserRole,
)
from tests.test_backend_api import (
    AUDITOR_PASSWORD,
    MFA_SECRET,
    backend,  # noqa: F401
    sign_in_auditor,
    sign_in_client,
)
from tests.test_workpapers_samples import _document, _sign_in, _teammates

NO = [{"id": f"q{i}", "answer": "no"} for i in range(1, 6)]


def _url(ids, tail=""):
    return f"/auditor/engagements/{ids['engagement_a']}{tail}"


def _partner(factory, ids) -> None:
    with factory() as db:
        practice = db.get(User, ids["auditor"]).practice_id
        db.add(
            User(
                email="partner-a@example.test",
                name="Pat Partner",
                role=UserRole.AUDITOR,
                password_hash=hash_password(AUDITOR_PASSWORD),
                mfa_secret=MFA_SECRET,
                mfa_enabled=True,
                accepted_at=datetime.now(UTC),
                practice_id=practice,
                team_role="partner",
            )
        )
        db.commit()


def _conclude_all(factory, ids) -> None:
    with factory() as db:
        for item in db.scalars(
            select(ChecklistItemInstance).where(
                ChecklistItemInstance.engagement_id == ids["engagement_a"]
            )
        ):
            item.conclusion = "pass"
        db.commit()


def _setup(backend):  # noqa: F811
    client, factory, ids, *_ = backend
    _teammates(factory, ids)
    _partner(factory, ids)
    return client, factory, ids


def test_independence_conclusions_and_audit(backend):  # noqa: F811
    client, factory, ids = _setup(backend)
    sign_in_auditor(client)
    start = client.get(_url(ids, "/independence")).json()
    assert start["conclusion"] is None and start["declaredBy"] is None
    assert [a["id"] for a in start["answers"]] == ["q1", "q2", "q3", "q4", "q5"]
    assert all(a["answer"] is None for a in start["answers"])
    partial = client.put(_url(ids, "/independence"), json={"answers": NO[:2]}).json()
    assert partial["conclusion"] is None and partial["answers"][0]["answer"] == "no"
    done = client.put(_url(ids, "/independence"), json={"answers": NO}).json()
    assert done["conclusion"] == "independent" and done["declaredBy"] == "Synthetic Auditor"
    yes = [{"id": "q1", "answer": "yes"}, *NO[1:]]
    body = {"answers": yes, "conflicts": "Held shares."}
    assert client.put(_url(ids, "/independence"), json=body).json()["conclusion"] == (
        "not_independent"
    )
    body["safeguards"] = "Divested."
    assert client.put(_url(ids, "/independence"), json=body).json()["conclusion"] == (
        "safeguards_required"
    )
    assert (
        client.put(_url(ids, "/independence"), json={"answers": [{"id": "q9"}]}).status_code == 422
    )
    assert client.put(_url(ids, "/independence"), json={"answers": NO, "x": 1}).status_code == 422
    with factory() as db:
        log = db.scalars(select(AuditLog).where(AuditLog.action == "independence.recorded")).all()
        assert log and all(row.firm_id == ids["firm_a"] for row in log)
        assert "Held shares." not in str([row.details for row in log])


def test_full_signoff_flow_and_client_report(backend):  # noqa: F811
    client, factory, ids = _setup(backend)
    document = _document(factory, ids)
    with factory() as db:
        db.add(
            Finding(
                firm_id=ids["firm_a"],
                engagement_id=ids["engagement_a"],
                title="Secret finding",
                rule="r",
                condition="Confidential condition text",
                cause="c",
                effect="e",
                recommendation="rec",
                severity="high",
                citations=[{"document": "synthetic-evidence.txt", "page": 1}],
                status="approved",
                created_by_id=ids["auditor"],
            )
        )
        db.commit()
    assert document
    sign_in_auditor(client)
    blockers = client.get(_url(ids, "/signoff/blockers")).json()
    assert any("no conclusion" in b for b in blockers)
    assert "Independence has not been cleared." in blockers
    assert client.put(_url(ids, "/independence"), json={"answers": NO}).status_code == 200
    _conclude_all(factory, ids)
    assert client.get(_url(ids, "/signoff/blockers")).json() == []
    state = client.get(_url(ids, "/signoff")).json()
    assert state == {
        "engagementId": ids["engagement_a"],
        "reviewer": {"name": "", "approvedAt": None, "note": ""},
        "partner": {"name": "", "signedAt": None, "fingerprint": None},
        "completedAt": None,
    }
    # The preparer, a plain colleague and a foreign reviewer cannot approve.
    assert client.post(_url(ids, "/signoff/review"), json={}).status_code == 403
    _sign_in(client, "colleague-a@example.test")  # not assigned, not a reviewer: cannot see it
    assert client.post(_url(ids, "/signoff/review"), json={}).status_code == 404
    _sign_in(client, "reviewer-b@example.test")
    assert client.post(_url(ids, "/signoff/review"), json={}).status_code == 404
    with factory() as db:
        db.get(User, ids["auditor"]).team_role = "reviewer"
        db.commit()
    sign_in_auditor(client)
    assert client.post(_url(ids, "/signoff/review"), json={}).status_code == 409
    # A reviewer of the practice approves.
    _sign_in(client, "reviewer-a@example.test")
    approved = client.post(_url(ids, "/signoff/review"), json={"note": "Looks right."})
    assert approved.status_code == 200 and approved.json()["reviewer"]["note"] == "Looks right."
    assert approved.json()["reviewer"]["name"] == "reviewer-a"
    assert client.post(_url(ids, "/signoff/review"), json={}).status_code == 409
    # The reviewer cannot sign as partner; the preparer is not a partner.
    assert client.post(_url(ids, "/signoff/partner"), json={"typedName": "x"}).status_code == 403
    sign_in_auditor(client)
    assert client.post(_url(ids, "/signoff/partner"), json={"typedName": "x"}).status_code == 403
    assert client.put(_url(ids, "/independence"), json={"answers": NO}).status_code == 409
    # Partner: wrong name, then the right one.
    _sign_in(client, "partner-a@example.test")
    assert client.post(_url(ids, "/complete")).status_code == 409
    wrong = client.post(_url(ids, "/signoff/partner"), json={"typedName": "Someone Else"})
    assert wrong.status_code == 422
    signed = client.post(_url(ids, "/signoff/partner"), json={"typedName": " pat partner "})
    assert signed.status_code == 200
    body = signed.json()
    assert body["partner"]["name"] == "Pat Partner" and body["completedAt"] is None
    fingerprint = body["partner"]["fingerprint"]
    with factory() as db:
        row = db.scalar(select(EngagementSignoff))
        sections = row.signed_sections
        text = "\n\n".join(f"{s['title']}\n{s['body']}" for s in sections)
        assert fingerprint == hashlib.sha256(text.encode()).hexdigest()
        assert any(s["id"].startswith("finding-") for s in sections)
        details = db.scalar(
            select(AuditLog.details).where(AuditLog.action == "signoff.partner_signed")
        )
        assert details["fingerprint"] == fingerprint
    assert (
        client.post(_url(ids, "/signoff/partner"), json={"typedName": "Pat Partner"}).status_code
        == 409
    )
    # Signed text is locked.
    sign_in_auditor(client)
    locked = client.put(_url(ids, "/report-draft/sections/scope"), json={"body": "changed"})
    assert locked.status_code == 409
    # The client sees nothing until the engagement is complete.
    sign_in_client(client)
    hidden = client.get(f"/engagements/{ids['engagement_a']}/signed-report").json()
    assert hidden["available"] is False and hidden["sections"] == []
    _sign_in(client, "partner-a@example.test")
    done = client.post(_url(ids, "/complete"))
    assert done.status_code == 200 and done.json()["completedAt"] is not None
    assert client.post(_url(ids, "/complete")).status_code == 409
    with factory() as db:
        assert db.get(Engagement, ids["engagement_a"]).status.value == "complete"
    sign_in_client(client)
    report = client.get(f"/engagements/{ids['engagement_a']}/signed-report")
    assert report.status_code == 200
    view = report.json()
    assert set(view) == {
        "id",
        "period",
        "available",
        "signedOn",
        "signedBy",
        "fingerprint",
        "sections",
        "confirmed",
        "confirmedAt",
    }
    assert view["available"] is True and view["signedBy"] == "Pat Partner"
    assert view["fingerprint"] == fingerprint
    assert {s["id"] for s in view["sections"]} >= {"scope", "results", "limitations"}
    assert not any(s["id"].startswith("finding-") for s in view["sections"])
    assert "Confidential" not in report.text and "Secret finding" not in report.text


def test_blockers_stop_review_and_sign(backend):  # noqa: F811
    client, factory, ids = _setup(backend)
    sign_in_auditor(client)
    _sign_in(client, "reviewer-a@example.test")
    refused = client.post(_url(ids, "/signoff/review"), json={})
    assert refused.status_code == 409 and "blockers" in refused.json()["detail"]
    with factory() as db:
        assert db.scalar(select(EngagementSignoff.reviewer_approved_at)) is None


def test_client_cannot_use_auditor_routes_and_foreign_client_denied(backend):  # noqa: F811
    client, factory, ids = _setup(backend)
    sign_in_client(client)
    assert client.get(_url(ids, "/signoff")).status_code == 403
    assert client.post(_url(ids, "/signoff/partner"), json={"typedName": "x"}).status_code == 403
    sign_in_auditor(client)
    assert client.get(f"/engagements/{ids['engagement_a']}/signed-report").status_code == 403


def test_signoff_migration_up_down_and_idempotent():
    config = Config("alembic.ini")
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with engine.begin() as connection:
        config.attributes["connection"] = connection
        command.stamp(config, "a126_engagement_signoffs")
        command.downgrade(config, "a125_report_section_edits")
        assert "engagement_signoffs" not in set(inspect(connection).get_table_names())
        command.upgrade(config, "a126_engagement_signoffs")
        assert "engagement_signoffs" in set(inspect(connection).get_table_names())
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with engine.begin() as connection:
        config.attributes["connection"] = connection
        command.stamp(config, "a125_report_section_edits")
        command.upgrade(config, "a126_engagement_signoffs")
    engine.dispose()
