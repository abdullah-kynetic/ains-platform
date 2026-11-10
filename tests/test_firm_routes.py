"""L2-6a: practice team, branding, rubric and templates. Scope comes from the session only."""

from datetime import UTC, datetime

import pyotp
import pytest
from sqlalchemy import select

from app.auth.security import hash_password
from app.database.models import (
    AuditLog,
    AuthSession,
    Engagement,
    Practice,
    PracticeTemplate,
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

TEAM = "/auditor/firm/team"
TEMPLATES = "/auditor/firm/request-templates"


def _auditor(db, email: str, practice_id, role: str | None) -> User:
    user = User(
        email=email,
        name=email.split("@")[0],
        role=UserRole.AUDITOR,
        password_hash=hash_password(AUDITOR_PASSWORD),
        mfa_secret=MFA_SECRET,
        mfa_enabled=True,
        accepted_at=datetime.now(UTC),
        practice_id=practice_id,
        team_role=role,
    )
    db.add(user)
    db.flush()
    return user


def _sign_in(client, email: str) -> None:
    client.cookies.clear()
    response = client.post(
        "/auth/password",
        json={
            "email": email,
            "password": AUDITOR_PASSWORD,
            "mfa_code": pyotp.TOTP(MFA_SECRET).now(),
        },
    )
    assert response.status_code == 200, response.text


@pytest.fixture
def practices(backend):  # noqa: F811
    """Practice A (the fixture auditor is its partner) and an unrelated practice B."""
    client, factory, ids, *_ = backend
    with factory() as db:
        a = Practice(name="Synthetic Practice A", tagline="A tagline")
        b = Practice(name="Synthetic Practice B")
        db.add_all([a, b])
        db.flush()
        partner = db.get(User, ids["auditor"])
        partner.practice_id, partner.team_role = a.id, "partner"
        _auditor(db, "plain-a@example.test", a.id, "auditor")
        _auditor(db, "admin-a@example.test", a.id, "admin")
        _auditor(db, "partner-b@example.test", b.id, "partner")
        db.add(
            PracticeTemplate(
                practice_id=b.id, name="B template", kind="custom", request_ids=["AML-BD-001"]
            )
        )
        db.commit()
        out = {"a": a.id, "b": b.id}
    return client, factory, ids, out


def test_no_practice_and_client_are_denied(backend):  # noqa: F811
    client, _factory, ids, *_ = backend
    sign_in_auditor(client)  # fixture auditor has no practice yet
    assert client.get(TEAM).status_code == 403
    client.cookies.clear()
    sign_in_client(client)
    for path in (TEAM, "/auditor/firm/branding", "/auditor/firm/rubric", TEMPLATES):
        assert client.get(path).status_code == 403, path


def test_team_lifecycle_and_partner_guards(practices):
    client, factory, ids, p = practices
    sign_in_auditor(client)
    team = client.get(TEAM).json()
    assert {m["email"] for m in team} == {
        "auditor@example.test",
        "plain-a@example.test",
        "admin-a@example.test",
    }
    assert "partner-b@example.test" not in str(team)
    assert set(team[0]) == {"id", "name", "email", "role", "status"}

    invited = client.post(TEAM, json={"email": "New.Hire@Example.test", "role": "reviewer"})
    assert invited.status_code == 201
    new = next(m for m in invited.json() if m["email"] == "new.hire@example.test")
    assert new["status"] == "invited" and new["role"] == "reviewer"
    assert (
        client.post(TEAM, json={"email": "new.hire@example.test", "role": "auditor"}).status_code
        == 409
    )
    assert client.post(TEAM, json={"email": "not-an-email", "role": "auditor"}).status_code == 422
    assert client.post(TEAM, json={"email": "x@example.test", "role": "owner"}).status_code == 422
    with factory() as db:  # held inactive; cannot sign in
        assert db.scalar(select(User).where(User.id == new["id"])).is_active is False

    changed = client.patch(f"{TEAM}/{new['id']}", json={"role": "auditor"}).json()
    assert next(m for m in changed if m["id"] == new["id"])["role"] == "auditor"
    # The only partner cannot step down, be removed, or remove themselves.
    me = ids["auditor"]
    assert client.patch(f"{TEAM}/{me}", json={"role": "admin"}).status_code == 409
    assert client.delete(f"{TEAM}/{me}").status_code == 409
    # Never-signed-in invitees are deleted outright.
    after = client.delete(f"{TEAM}/{new['id']}").json()
    assert new["id"] not in {m["id"] for m in after}
    with factory() as db:
        assert db.get(User, new["id"]) is None
        actions = set(db.scalars(select(AuditLog.action)))
        assert {"team.invited", "team.role_changed", "team.removed"} <= actions
        assert all(
            row.firm_id is None and row.details["practice_id"] == p["a"]
            for row in db.scalars(select(AuditLog).where(AuditLog.action.like("team.%")))
        )


def test_removal_deactivates_a_member_and_ends_their_sessions(practices):
    client, factory, ids, p = practices
    plain = next(m for m in _team(client) if m["email"] == "plain-a@example.test")
    _sign_in(client, "plain-a@example.test")
    assert client.get(TEAM).status_code == 200
    sign_in_auditor(client)
    assert client.delete(f"{TEAM}/{plain['id']}").status_code == 200
    with factory() as db:
        user = db.get(User, plain["id"])
        assert user.is_active is False and user.practice_id is None and user.team_role is None
        assert all(
            s.revoked_at is not None
            for s in db.scalars(select(AuthSession).where(AuthSession.user_id == plain["id"]))
        )
    _sign_in_denied(client, "plain-a@example.test")


def test_removal_is_blocked_while_engagements_are_assigned(practices):
    client, factory, ids, p = practices
    plain = next(m for m in _team(client) if m["email"] == "plain-a@example.test")
    with factory() as db:
        db.get(Engagement, ids["engagement_a"]).auditor_id = plain["id"]
        db.commit()
    sign_in_auditor(client)
    assert client.delete(f"{TEAM}/{plain['id']}").status_code == 409


def test_roles_limit_who_can_change_what(practices):
    client, factory, ids, p = practices
    team = {m["email"]: m for m in _team(client)}
    _sign_in(client, "plain-a@example.test")
    assert client.post(TEAM, json={"email": "z@example.test", "role": "auditor"}).status_code == 403
    assert client.put("/auditor/firm/branding", json={"name": "X"}).status_code == 403
    assert client.put("/auditor/firm/rubric/AML-BD-001", json={"criteria": "x"}).status_code == 403
    _sign_in(client, "admin-a@example.test")
    # An admin manages the team but cannot grant, change or remove a partner.
    assert client.post(TEAM, json={"email": "z@example.test", "role": "partner"}).status_code == 403
    assert client.post(TEAM, json={"email": "z@example.test", "role": "auditor"}).status_code == 201
    partner_id = team["auditor@example.test"]["id"]
    assert client.patch(f"{TEAM}/{partner_id}", json={"role": "admin"}).status_code == 403
    assert client.delete(f"{TEAM}/{partner_id}").status_code == 403
    assert client.put("/auditor/firm/rubric/AML-BD-001", json={"criteria": "x"}).status_code == 403


def test_branding_never_stores_a_data_url_and_is_per_practice(practices):
    client, factory, ids, p = practices
    sign_in_auditor(client)
    assert client.get("/auditor/firm/branding").json() == {
        "name": "Synthetic Practice A",
        "logoDataUrl": None,
        "tagline": "A tagline",
    }
    body = {"name": " New name ", "tagline": "t", "logoDataUrl": "https://cdn.example.test/l.png"}
    saved = client.put("/auditor/firm/branding", json=body)
    assert saved.status_code == 200
    assert saved.json() == {
        "name": "New name",
        "logoDataUrl": "https://cdn.example.test/l.png",
        "tagline": "t",
    }
    for bad in ("data:image/png;base64,AAAA", "http://x.test/l.png", "https://u:p@x.test/l.png"):
        assert (
            client.put("/auditor/firm/branding", json={**body, "logoDataUrl": bad}).status_code
            == 422
        )
    assert client.put("/auditor/firm/branding", json={"name": "  "}).status_code == 422
    _sign_in(client, "partner-b@example.test")
    assert client.get("/auditor/firm/branding").json()["name"] == "Synthetic Practice B"
    with factory() as db:
        assert db.get(Practice, p["a"]).name == "New name"


def test_rubric_defaults_empty_and_only_a_partner_writes_criteria(practices):
    client, factory, ids, p = practices
    sign_in_auditor(client)
    rubric = client.get("/auditor/firm/rubric").json()
    assert len(rubric) == 34
    assert set(rubric[0]) == {"requestId", "title", "section", "criteria", "enabled"}
    assert all(item["criteria"] == "" and item["enabled"] for item in rubric)
    one = client.put(
        "/auditor/firm/rubric/AML-BD-002",
        json={"requestId": "AML-BD-002", "title": "ignored", "criteria": " c ", "enabled": False},
    )
    assert one.status_code == 200
    assert (one.json()["requestId"], one.json()["criteria"], one.json()["enabled"]) == (
        "AML-BD-002",
        "c",
        False,
    )
    assert one.json()["title"] != "ignored"
    assert client.put("/auditor/firm/rubric/AML-BD-999", json={"criteria": "x"}).status_code == 404
    assert (
        client.put("/auditor/firm/rubric/AML-BD-001", json={"criteria": "x" * 4001}).status_code
        == 422
    )
    _sign_in(client, "partner-b@example.test")
    other = {i["requestId"]: i for i in client.get("/auditor/firm/rubric").json()}
    assert other["AML-BD-002"]["criteria"] == "" and other["AML-BD-002"]["enabled"] is True


def test_templates_crud_validation_and_foreign_practice_denial(practices):
    client, factory, ids, p = practices
    sign_in_auditor(client)
    start = client.get(TEMPLATES).json()
    assert [t["id"] for t in start] == ["tpl-all"] and len(start[0]["requestIds"]) == 34
    assert "B template" not in str(start)
    body = {
        "name": "Mine",
        "kind": "retail",
        "description": "d",
        "requestIds": ["AML-BD-001", "AML-BD-002"],
    }
    created = client.post(TEMPLATES, json=body)
    assert created.status_code == 201
    mine = next(t for t in created.json() if t["name"] == "Mine")
    assert mine["requestIds"] == body["requestIds"] and mine["kind"] == "retail"
    for bad in (
        {**body, "requestIds": []},
        {**body, "requestIds": ["AML-BD-001", "AML-BD-001"]},
        {**body, "requestIds": ["AML-BD-777"]},
        {**body, "kind": "other"},
        {**body, "name": " "},
    ):
        assert client.post(TEMPLATES, json=bad).status_code == 422
    updated = client.put(f"{TEMPLATES}/{mine['id']}", json={**body, "name": "Renamed"}).json()
    assert {t["name"] for t in updated} == {"Full Rule 3310 request list", "Renamed"}
    assert client.put(f"{TEMPLATES}/tpl-all", json=body).status_code == 409
    assert client.delete(f"{TEMPLATES}/tpl-all").status_code == 409
    # Practice B's real template and member ids look like nothing at all from practice A.
    with factory() as db:
        foreign_template = db.scalar(
            select(PracticeTemplate.id).where(PracticeTemplate.practice_id == p["b"])
        )
        foreign_member = db.scalar(select(User.id).where(User.email == "partner-b@example.test"))
    assert client.put(f"{TEMPLATES}/{foreign_template}", json=body).status_code == 404
    assert client.delete(f"{TEMPLATES}/{foreign_template}").status_code == 404
    assert client.patch(f"{TEAM}/{foreign_member}", json={"role": "auditor"}).status_code == 404
    assert client.delete(f"{TEAM}/{foreign_member}").status_code == 404
    with factory() as db:
        assert db.get(PracticeTemplate, foreign_template) is not None
        assert db.get(User, foreign_member).is_active is True
    assert client.delete(f"{TEMPLATES}/{mine['id']}").status_code == 200


def _team(client):
    sign_in_auditor(client)
    return client.get(TEAM).json()


def _sign_in_denied(client, email: str) -> None:
    client.cookies.clear()
    response = client.post(
        "/auth/password",
        json={
            "email": email,
            "password": AUDITOR_PASSWORD,
            "mfa_code": pyotp.TOTP(MFA_SECRET).now(),
        },
    )
    assert response.status_code == 401
