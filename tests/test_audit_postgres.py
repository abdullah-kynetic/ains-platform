"""Exercise the migration and concurrent appends in an isolated synthetic Postgres cluster."""

import shutil
import socket
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.audit import verify
from app.database.models import AuditLog, Base


@pytest.fixture
def postgres_engine(tmp_path):
    candidates = sorted(Path("/usr/lib/postgresql").glob("*/bin/initdb"))
    initdb = shutil.which("initdb") or (str(candidates[-1]) if candidates else None)
    if not initdb:
        pytest.skip("Local Postgres binaries are needed for the isolated trigger integration test")
    binary = Path(initdb).parent
    data = tmp_path / "pg"
    sockets = tmp_path / "socket"
    sockets.mkdir()
    with socket.socket() as available:
        available.bind(("127.0.0.1", 0))
        port = available.getsockname()[1]
    subprocess.run(
        [initdb, "-D", str(data), "-A", "trust", "-U", "synthetic"], check=True, capture_output=True
    )
    subprocess.run(
        [
            str(binary / "pg_ctl"),
            "-D",
            str(data),
            "-l",
            str(tmp_path / "pg.log"),
            "-o",
            f"-k {sockets} -p {port} -c listen_addresses=''",
            "-w",
            "start",
        ],
        check=True,
        capture_output=True,
    )
    engine = create_engine(
        "postgresql+psycopg://synthetic@/postgres",
        connect_args={"host": str(sockets), "port": port},
    )
    try:
        yield engine
    finally:
        engine.dispose()
        subprocess.run(
            [str(binary / "pg_ctl"), "-D", str(data), "-m", "immediate", "stop"],
            check=True,
            capture_output=True,
        )


def test_postgres_backfill_trigger_and_concurrent_appends(postgres_engine):
    engine = postgres_engine
    Base.metadata.create_all(engine)
    config = Config("alembic.ini")
    with engine.begin() as connection:
        config.attributes["connection"] = connection
        connection.execute(text("ALTER TABLE audit_logs DROP CONSTRAINT uq_audit_firm_sequence"))
        for column in ("ip_address", "sequence", "previous_hash", "row_hash"):
            connection.execute(text(f"ALTER TABLE audit_logs DROP COLUMN {column}"))
        command.stamp(config, "a109_password_reset")
        connection.execute(
            text("""INSERT INTO audit_logs
            (id, action, entity_type, details, created_at)
            VALUES ('synthetic-legacy', 'legacy.view', 'engagement', '{}', now())""")
        )
        command.upgrade(config, "head")
    with Session(engine) as db:
        rows = db.scalars(select(AuditLog).order_by(AuditLog.sequence)).all()
        assert verify(rows) == {"valid": True, "checked": 1, "broken_at": None}
    for sql in [
        "UPDATE audit_logs SET action='tampered'",
        "DELETE FROM audit_logs",
        "TRUNCATE audit_logs",
    ]:
        with engine.connect() as connection, pytest.raises(DBAPIError, match="append-only"):
            connection.execute(text(sql))

    def append(index):
        with Session(engine) as db:
            db.info["ip_address"] = "192.0.2.20"
            db.add(
                AuditLog(action="synthetic.view", entity_type="engagement", entity_id=str(index))
            )
            db.commit()

    with ThreadPoolExecutor(max_workers=4) as workers:
        list(workers.map(append, range(12)))
    with Session(engine) as db:
        rows = db.scalars(select(AuditLog).order_by(AuditLog.sequence)).all()
        assert verify(rows) == {"valid": True, "checked": 13, "broken_at": None}
        assert rows[-1].ip_address == "192.0.2.20"

    with engine.begin() as connection:
        config.attributes["connection"] = connection
        command.downgrade(config, "a109_password_reset")
