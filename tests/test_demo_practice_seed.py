"""The live demo seed: idempotent, synthetic-only, secrets only in a 600 file."""

import os
import stat

import pytest
from sqlalchemy import select

from app.database.models import Engagement, Firm, Practice, User
from app.demo_practice_seed import RefusedError, seed
from tests.test_backend_api import backend  # noqa: F401


@pytest.fixture
def empty(tmp_path):
    """A brand-new empty database (the audit log is append-only, so rows are never deleted)."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app.database.models import Base

    engine = create_engine(f"sqlite+pysqlite:///{tmp_path / 'demo.db'}")
    Base.metadata.create_all(engine)
    return sessionmaker(engine, expire_on_commit=False)


def test_seeds_two_firms_one_unassigned_and_writes_credentials_privately(empty, tmp_path):
    factory = empty
    path = str(tmp_path / "creds.txt")
    with factory() as db:
        summary = seed(db, credentials_file=path)
    assert summary["passwordsWritten"] == 3
    assert stat.S_IMODE(os.stat(path).st_mode) == 0o600
    text = open(path).read()
    assert "demo-quentin@example.test" in text
    with factory() as db:
        practice = db.scalar(select(Practice))
        assert practice.allow_auditor_as_signer is True
        quentin = db.scalar(select(User).where(User.email == "demo-quentin@example.test"))
        assert quentin.team_role == "partner" and quentin.password_hash
        assert "synthetic" not in quentin.password_hash.lower()
        engagements = {e.firm.slug: e.auditor_id for e in db.scalars(select(Engagement))}
        assert engagements == {"demo-securities": quentin.id, "demo-other": None}
        # No password appears in any database column in clear text.
        assert not any(line.split()[-1] in quentin.password_hash for line in text.splitlines()[1:])


def test_second_run_changes_nothing_and_never_overwrites_the_file(empty, tmp_path):
    factory = empty
    path = str(tmp_path / "creds.txt")
    with factory() as db:
        seed(db, credentials_file=path)
    before = open(path).read()
    with factory() as db:
        again = seed(db, credentials_file=path)
        assert again["created"] == [] and again["passwordsWritten"] == 0
        assert len(db.scalars(select(Firm)).all()) == 2
    assert open(path).read() == before


def test_refuses_when_other_firms_exist(backend, tmp_path):  # noqa: F811
    _, factory, *_ = backend  # the fixture already holds non-demo firms
    with factory() as db, pytest.raises(RefusedError):
        seed(db, credentials_file=str(tmp_path / "creds.txt"))
    assert not (tmp_path / "creds.txt").exists()


def test_dash_sends_credentials_to_stdout_only(empty, capsys):
    with empty() as db:
        summary = seed(db, credentials_file="-")
    out = capsys.readouterr().out
    assert "demo-quentin@example.test" in out and summary["passwordsWritten"] == 3


def test_demo_accounts_have_no_authenticator_and_old_enrollment_is_switched_off(empty, tmp_path):
    factory = empty
    path = str(tmp_path / "creds.txt")
    with factory() as db:
        seed(db, credentials_file=path)
        for user in db.scalars(select(User)):
            assert user.mfa_enabled is False and user.mfa_secret is None
        quentin = db.scalar(select(User).where(User.email == "demo-quentin@example.test"))
        quentin.mfa_enabled, quentin.mfa_secret = True, "JBSWY3DPEHPK3PXP"  # old TOTP enrollment
        db.commit()
    with factory() as db:
        seed(db, credentials_file=path)
        db.expire_all()
        quentin = db.scalar(select(User).where(User.email == "demo-quentin@example.test"))
        assert quentin.mfa_enabled is False and quentin.mfa_secret is None
