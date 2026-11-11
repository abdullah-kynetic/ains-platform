"""L2-9: scripts/e2e_seed.py puts four known engagement states in front of the real routes."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.dependencies import get_current_user
from app.database.models import Base, Engagement, Firm, Invoice, User
from app.database.session import get_db
from app.main import create_app
from scripts.e2e_seed import USERS, seed_workflow_fixtures


@pytest.fixture
def world():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)
    with factory() as db:
        result = seed_workflow_fixtures(db)
    current = [None]

    def database():
        with factory() as db:
            yield db

    def user():
        with factory() as db:
            return db.scalar(select(User).where(User.email == USERS[current[0]]))

    app = create_app()
    app.dependency_overrides[get_db] = database
    app.dependency_overrides[get_current_user] = user
    with TestClient(app) as client:
        yield client, factory, result, current
    engine.dispose()


def test_seed_is_idempotent_and_leaves_the_original_e2e_firm_alone(world):
    client, factory, result, current = world
    assert result["created"] is True and set(result["engagements"]) == {
        "testing",
        "ready",
        "signed",
        "confirmed",
    }
    with factory() as db:
        before = (
            db.scalar(select(func.count()).select_from(Engagement)),
            db.scalar(select(func.count()).select_from(User)),
        )
        again = seed_workflow_fixtures(db)
        assert again["created"] is False and again["engagements"] == result["engagements"]
        after = (
            db.scalar(select(func.count()).select_from(Engagement)),
            db.scalar(select(func.count()).select_from(User)),
        )
        assert before == after == (4, 4)
        assert db.scalar(select(Firm.slug)) == "kynetic-flow"


def test_testing_engagement_has_blockers_and_ready_has_none(world):
    client, factory, result, current = world
    current[0] = "auditor"
    path = "/auditor/engagements/{}/signoff/blockers"
    assert client.get(path.format(result["engagements"]["testing"])).json()
    assert client.get(path.format(result["engagements"]["ready"])).json() == []


def test_ready_engagement_walks_review_sign_complete_confirm_for_real(world):
    client, factory, result, current = world
    eid = result["engagements"]["ready"]
    audit = f"/auditor/engagements/{eid}"
    current[0] = "reviewer"
    assert client.post(f"{audit}/signoff/review", json={"note": "ok"}).status_code == 200
    current[0] = "partner"
    sign = client.post(f"{audit}/signoff/partner", json={"typedName": "Synthetic Flow Partner"})
    assert sign.status_code == 200
    assert client.post(f"{audit}/complete").status_code == 200
    current[0] = "client"
    report = client.get(f"/engagements/{eid}/signed-report").json()
    assert report["available"] and report["confirmed"] is False
    confirm = client.post(
        f"/engagements/{eid}/signed-report/confirm", json={"fingerprint": report["fingerprint"]}
    )
    assert confirm.status_code == 200 and confirm.json()["confirmed"] is True


def test_signed_and_confirmed_states_match_what_the_specs_expect(world):
    client, factory, result, current = world
    current[0] = "client"
    signed = client.get(f"/engagements/{result['engagements']['signed']}/signed-report").json()
    assert signed["available"] is True and signed["confirmed"] is False
    assert "Synthetic finding text" not in str(signed)
    confirmed = client.get(
        f"/engagements/{result['engagements']['confirmed']}/signed-report"
    ).json()
    assert confirmed["confirmed"] is True
    invoices = client.get(f"/engagements/{result['engagements']['confirmed']}/invoices").json()
    assert [i["status"] for i in invoices] == ["sent"]
    assert (
        client.get(f"/engagements/{result['engagements']['testing']}/signed-report").json()[
            "available"
        ]
        is False
    )
    with factory() as db:
        assert db.scalar(select(func.count()).select_from(Invoice)) == 1
    # The reviewer and partner cannot approve their own preparation, and cannot sign twice.
    current[0] = "partner"
    again = client.post(
        f"/auditor/engagements/{result['engagements']['signed']}/signoff/partner",
        json={"typedName": "Synthetic Flow Partner"},
    )
    assert again.status_code == 409
