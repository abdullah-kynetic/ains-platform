"""Per-practice setting: may the assigned auditor also sign as partner? (decision 2026-11-10)."""

from sqlalchemy import select

from app.database.models import AuditLog, Practice, User
from tests.test_backend_api import backend, sign_in_auditor  # noqa: F401
from tests.test_signoff import NO, _conclude_all, _setup, _url
from tests.test_workpapers_samples import _sign_in

SETTING = "/auditor/firm/signoff-settings"


def _ready_for_partner(client, factory, ids):
    """Quentin-style setup: the assigned auditor is the partner; a separate reviewer approves."""
    with factory() as db:
        db.get(User, ids["auditor"]).team_role = "partner"
        db.commit()
    _conclude_all(factory, ids)
    sign_in_auditor(client)
    assert client.put(_url(ids, "/independence"), json={"answers": NO}).status_code == 200
    _sign_in(client, "reviewer-a@example.test")
    assert client.post(_url(ids, "/signoff/review"), json={}).status_code == 200
    sign_in_auditor(client)


def _name(factory, ids) -> str:
    with factory() as db:
        return db.get(User, ids["auditor"]).name


def test_default_off_blocks_assigned_auditor_from_signing(backend):  # noqa: F811
    client, factory, ids = _setup(backend)
    _ready_for_partner(client, factory, ids)
    assert client.get(SETTING).json() == {"allowAuditorAsSigner": False}
    refused = client.post(_url(ids, "/signoff/partner"), json={"typedName": _name(factory, ids)})
    assert refused.status_code == 409


def test_setting_on_allows_it_and_records_the_decision(backend):  # noqa: F811
    client, factory, ids = _setup(backend)
    _ready_for_partner(client, factory, ids)
    changed = client.put(SETTING, json={"allowAuditorAsSigner": True})
    assert changed.status_code == 200 and changed.json() == {"allowAuditorAsSigner": True}
    signed = client.post(_url(ids, "/signoff/partner"), json={"typedName": _name(factory, ids)})
    assert signed.status_code == 200
    with factory() as db:
        setting = db.scalar(
            select(AuditLog).where(AuditLog.action == "practice.signoff_setting_changed")
        )
        assert setting.details["allow_auditor_as_signer"] is True
        assert setting.details["previous"] is False
        details = db.scalar(
            select(AuditLog.details).where(AuditLog.action == "signoff.partner_signed")
        )
        assert details["auditor_is_signer"] is True
        assert details["practice_allows_auditor_as_signer"] is True


def test_reviewer_must_still_be_a_different_user(backend):  # noqa: F811
    client, factory, ids = _setup(backend)
    with factory() as db:
        practice = db.get(User, ids["auditor"]).practice_id
        db.get(Practice, practice).allow_auditor_as_signer = True
        db.get(User, ids["auditor"]).team_role = "reviewer"
        db.commit()
    sign_in_auditor(client)
    assert client.post(_url(ids, "/signoff/review"), json={}).status_code == 409


def test_only_partner_or_admin_changes_it_and_it_is_per_practice(backend):  # noqa: F811
    client, factory, ids = _setup(backend)
    sign_in_auditor(client)  # team role "auditor" by default
    assert client.put(SETTING, json={"allowAuditorAsSigner": True}).status_code == 403
    with factory() as db:
        db.get(User, ids["auditor"]).team_role = "partner"
        db.commit()
    assert client.put(SETTING, json={"allowAuditorAsSigner": True}).status_code == 200
    # Practice B's reviewer sees its own practice's value, not practice A's.
    _sign_in(client, "reviewer-b@example.test")
    assert client.get(SETTING).json() == {"allowAuditorAsSigner": False}
    with factory() as db:
        values = {p.name: p.allow_auditor_as_signer for p in db.scalars(select(Practice))}
    assert values["Synthetic A"] is True and values["Synthetic B"] is False


def test_clients_and_anonymous_cannot_reach_it(backend):  # noqa: F811
    client, *_ = backend
    assert client.get(SETTING).status_code == 401
    from tests.test_backend_api import sign_in_client

    sign_in_client(client)
    assert client.get(SETTING).status_code == 403
    assert client.put(SETTING, json={"allowAuditorAsSigner": True}).status_code == 403
