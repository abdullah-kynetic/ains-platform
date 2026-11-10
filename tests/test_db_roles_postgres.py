"""Least-privilege DB roles (deploy/bootstrap/db-roles.sql) against a real Postgres (CI service).

kien_app may read and write app tables but never CREATE or DROP; kien_backup is read-only.
"""

import os
import shutil
import subprocess
import uuid

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError

SQL = "deploy/bootstrap/db-roles.sql"


@pytest.fixture
def roles_db():
    if "KIEN_TEST_POSTGRES_URL" not in os.environ:
        pytest.skip("KIEN_TEST_POSTGRES_URL not set (CI provides a synthetic Postgres)")
    assert shutil.which("psql"), "psql client is required for this test"
    url = make_url(os.environ["KIEN_TEST_POSTGRES_URL"])
    name = f"kien_roles_{uuid.uuid4().hex[:12]}"
    admin = create_engine(url, isolation_level="AUTOCOMMIT")
    with admin.connect() as c:
        c.execute(text(f'CREATE DATABASE "{name}"'))
    pw = {
        "KIEN_MIGRATOR_PASSWORD": "synthetic-m",
        "KIEN_APP_PASSWORD": "synthetic-a",
        "KIEN_BACKUP_PASSWORD": "synthetic-b",
    }
    env = {**os.environ, **pw, "PGPASSWORD": url.password or ""}
    subprocess.run(
        [
            "psql",
            "-q",
            "-v",
            "ON_ERROR_STOP=1",
            "-h",
            url.host or "localhost",
            "-p",
            str(url.port or 5432),
            "-U",
            url.username,
            "-d",
            name,
            "-f",
            SQL,
        ],
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )

    def engine(role: str, password: str):
        return create_engine(
            url.set(database=name, username=role, password=password), isolation_level="AUTOCOMMIT"
        )

    engines = {
        "migrator": engine("kien_migrator", pw["KIEN_MIGRATOR_PASSWORD"]),
        "app": engine("kien_app", pw["KIEN_APP_PASSWORD"]),
        "backup": engine("kien_backup", pw["KIEN_BACKUP_PASSWORD"]),
    }
    try:
        yield engines
    finally:
        for e in engines.values():
            e.dispose()
        with admin.connect() as c:
            c.execute(text(f'DROP DATABASE "{name}" WITH (FORCE)'))
        admin.dispose()


def test_app_role_has_dml_but_no_ddl(roles_db):
    with roles_db["migrator"].connect() as m:
        m.execute(text("CREATE TABLE engagements (id serial PRIMARY KEY, name text)"))
    with roles_db["app"].connect() as a:
        a.execute(text("INSERT INTO engagements (name) VALUES ('synthetic')"))
        a.execute(text("UPDATE engagements SET name = 'synthetic-2'"))
        assert a.execute(text("SELECT count(*) FROM engagements")).scalar() == 1
        a.execute(text("DELETE FROM engagements"))
        with pytest.raises(DBAPIError):
            a.execute(text("CREATE TABLE intruder (id int)"))
        with pytest.raises(DBAPIError):
            a.execute(text("DROP TABLE engagements"))
        with pytest.raises(DBAPIError):
            a.execute(text("ALTER TABLE engagements ADD COLUMN x int"))


def test_backup_role_is_read_only(roles_db):
    with roles_db["migrator"].connect() as m:
        m.execute(text("CREATE TABLE firms (id int)"))
        m.execute(text("INSERT INTO firms VALUES (1)"))
    with roles_db["backup"].connect() as b:
        assert b.execute(text("SELECT count(*) FROM firms")).scalar() == 1
        with pytest.raises(DBAPIError):
            b.execute(text("INSERT INTO firms VALUES (2)"))
        with pytest.raises(DBAPIError):
            b.execute(text("CREATE TABLE intruder (id int)"))
