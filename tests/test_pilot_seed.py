"""L2-9: the idempotent synthetic pilot seed. No network, no real addresses."""

import json

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from app.auth.email import ResendSender
from app.config import Settings
from app.database.models import (
    AuditLog,
    Base,
    ChecklistItemInstance,
    ClientInvitation,
    Engagement,
    Firm,
    Practice,
    User,
)
from app.pilot_seed import PILOT_FIRMS, seed


@pytest.fixture
def factory():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    yield sessionmaker(engine, expire_on_commit=False)
    engine.dispose()


def settings(**kw):
    return Settings(_env_file=None, **kw)


def count(db, model):
    return db.scalar(select(func.count()).select_from(model))


def test_seed_creates_three_firms_one_auditor_and_engagements_then_changes_nothing(factory):
    with factory() as db:
        first = seed(db, settings())
        assert first["firms"] == 3 and first["engagements"] == 3
        assert first["slugs"] == [slug for slug, _ in PILOT_FIRMS]
        assert first["invitationsCreated"] == 0 and first["invitationsSent"] == 0
    with factory() as db:
        assert {f.slug for f in db.scalars(select(Firm))} == {s for s, _ in PILOT_FIRMS}
        assert all("(synthetic)" in f.name for f in db.scalars(select(Firm)))
        auditor = db.scalar(select(User))
        assert auditor.email == "pilot-auditor@example.test" and auditor.password_hash is None
        assert auditor.team_role == "partner" and auditor.practice_id
        assert count(db, Practice) == 1 and count(db, Engagement) == 3
        assert all(e.auditor_id == auditor.id for e in db.scalars(select(Engagement)))
        assert count(db, ChecklistItemInstance) == 3 * 34
    with factory() as db:
        again = seed(db, settings())
        assert again["firms"] == 0 and again["engagements"] == 0
        assert (count(db, Firm), count(db, Engagement), count(db, User)) == (3, 3, 1)
        assert count(db, ChecklistItemInstance) == 3 * 34


def test_password_is_set_only_when_configured_and_never_returned(factory):
    with factory() as db:
        out = seed(db, settings(demo_password="synthetic-only-password"))
        assert "synthetic-only-password" not in json.dumps(out)
        assert db.scalar(select(User.password_hash))


def test_refuses_invitation_preview_in_production(factory):
    with factory() as db, pytest.raises(RuntimeError, match="INVITATION_PREVIEW_ENABLED"):
        seed(db, settings(env="production", invitation_preview_enabled=True))
    with factory() as db:
        assert count(db, Firm) == 0


def test_invitations_are_created_without_sending_unless_asked(factory, monkeypatch):
    sent = []
    monkeypatch.setattr(ResendSender, "send", lambda self, **kw: sent.append(kw))
    cfg = settings(pilot_invitee_emails="One@example.test, two@example.test")
    with factory() as db:
        out = seed(db, cfg)
        assert out["invitationsCreated"] == 2 and out["invitationsSent"] == 0 and not sent
        emails = {i.email for i in db.scalars(select(ClientInvitation))}
        assert emails == {"one@example.test", "two@example.test"}
        # Only two addresses for three firms: the third firm has none.
        assert count(db, ClientInvitation) == 2
        assert all(
            i.token_hash and len(i.token_hash) == 64 for i in db.scalars(select(ClientInvitation))
        )
    with factory() as db:  # idempotent: no duplicates, still nothing sent
        assert seed(db, cfg, send=True)["invitationsCreated"] == 0
        assert not sent


def test_send_emails_each_new_invitation_once_and_records_the_audit_entry(factory, monkeypatch):
    sent = []
    monkeypatch.setattr(ResendSender, "send", lambda self, **kw: sent.append(kw))
    cfg = settings(pilot_invitee_emails="a@example.test,b@example.test,c@example.test")
    with factory() as db:
        out = seed(db, cfg, send=True)
        assert out["invitationsCreated"] == 3 and out["invitationsSent"] == 3
        assert {s["email"] for s in sent} == {"a@example.test", "b@example.test", "c@example.test"}
        assert {s["slug"] for s in sent} == {slug for slug, _ in PILOT_FIRMS}
        assert all(s["token"] for s in sent)
        dumped = json.dumps(out)
        assert not any(s["token"] in dumped for s in sent) and "@" not in dumped
        log = db.scalars(
            select(AuditLog).where(AuditLog.action == "client_invitation.created")
        ).all()
        assert len(log) == 3 and all(row.details["source"] == "pilot_seed" for row in log)
        assert all(s["token"] not in str(row.details) for s in sent for row in log)
    with factory() as db:
        seed(db, cfg, send=True)
    assert len(sent) == 3


def test_a_failed_delivery_leaves_no_invitation_so_the_next_run_retries(factory, monkeypatch):
    def fail(self, **kw):
        raise HTTPException(503, "Email delivery is not configured")

    monkeypatch.setattr(ResendSender, "send", fail)
    cfg = settings(pilot_invitee_emails="a@example.test")
    with factory() as db, pytest.raises(HTTPException):
        seed(db, cfg, send=True)
    with factory() as db:
        assert count(db, ClientInvitation) == 0
    sent = []
    monkeypatch.setattr(ResendSender, "send", lambda self, **kw: sent.append(kw))
    with factory() as db:
        assert seed(db, cfg, send=True)["invitationsSent"] == 1
    assert len(sent) == 1
