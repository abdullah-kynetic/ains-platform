"""Synthetic pg_dump restore drill.

Seed mock rows on a private Postgres cluster, write a custom-format dump
(``pg_dump -Fc``, the same archive shape as the daily backup), restore it into
a second database, and compare row counts for every public base table.

The drill does not accept a database URL, dump path, or S3 location. Fetching
a production object and restoring it by hand is documented in
``docs/backup-restore.md``.

Exit codes: 0 counts match, 1 a table count differs, 2 Postgres tools are
missing or arguments were passed.
"""

from __future__ import annotations

import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import create_engine, text  # noqa: E402
from sqlalchemy.engine import Engine  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402
from sqlalchemy.pool import NullPool  # noqa: E402

import app.audit  # noqa: E402
from app.database.models import (  # noqa: E402
    AuditLog,
    Base,
    ChecklistItemInstance,
    Document,
    Engagement,
    Firm,
    User,
    UserRole,
)

SOURCE_DATABASE = "ains_source"
RESTORE_DATABASE = "ains_restore"
CLUSTER_USER = "synthetic"
_IDENT = re.compile(r"^[a-z][a-z0-9_]*$")
_REQUIRED_BINARIES = ("initdb", "pg_ctl", "pg_dump", "pg_restore")

# Known mock population. Empty application tables are still compared.
SEEDED_COUNTS = {
    "firms": 1,
    "users": 2,
    "engagements": 1,
    "checklist_item_instances": 2,
    "documents": 1,
    "audit_logs": 1,
}


class PostgresUnavailable(RuntimeError):
    """Local initdb, pg_ctl, pg_dump, and pg_restore were not found together."""


class RestoreCountMismatch(RuntimeError):
    def __init__(self, mismatches: list[str]) -> None:
        super().__init__("\n".join(mismatches))
        self.mismatches = mismatches


@dataclass(frozen=True)
class PostgresBinaries:
    initdb: Path
    pg_ctl: Path
    pg_dump: Path
    pg_restore: Path


@dataclass(frozen=True)
class RestoreDrillResult:
    source_counts: dict[str, int]
    restored_counts: dict[str, int]
    dump_path: Path


@dataclass
class _Cluster:
    binaries: PostgresBinaries
    data_dir: Path
    socket_dir: Path
    port: int

    def engine(self, database: str) -> Engine:
        _check_ident(database)
        return create_engine(
            f"postgresql+psycopg://{CLUSTER_USER}@/{database}",
            connect_args={"host": str(self.socket_dir), "port": self.port},
            poolclass=NullPool,
        )


def locate_postgres_binaries() -> PostgresBinaries | None:
    """Find a single directory that contains the server and dump tools.

    ``initdb`` is often absent from ``PATH`` on Debian and Ubuntu. The
    versioned directory under ``/usr/lib/postgresql`` is checked as well, and
    the newest complete directory wins so dump and restore stay on one major
    version.
    """
    candidates: list[Path] = []
    discovered = shutil.which("initdb")
    if discovered:
        candidates.append(Path(discovered).parent)
    lib_root = Path("/usr/lib/postgresql")
    if lib_root.is_dir():
        candidates.extend(path.parent for path in sorted(lib_root.glob("*/bin/initdb")))
    seen: set[Path] = set()
    ordered: list[Path] = []
    for directory in candidates:
        resolved = directory.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        ordered.append(resolved)
    for directory in reversed(ordered):
        paths = {name: directory / name for name in _REQUIRED_BINARIES}
        if all(path.is_file() and os.access(path, os.X_OK) for path in paths.values()):
            return PostgresBinaries(**paths)
    return None


def compare_counts(source: dict[str, int], restored: dict[str, int]) -> list[str]:
    """Return one line per table whose row count differs, including missing tables."""
    mismatches: list[str] = []
    for name in sorted(set(source) | set(restored)):
        left = source.get(name)
        right = restored.get(name)
        if left != right:
            mismatches.append(f"{name}: source={left} restored={right}")
    return mismatches


def table_counts(engine: Engine) -> dict[str, int]:
    """Exact row counts for every ordinary table in ``public``."""
    counts: dict[str, int] = {}
    with engine.connect() as connection:
        names = connection.execute(
            text(
                """
                SELECT c.relname
                FROM pg_catalog.pg_class AS c
                JOIN pg_catalog.pg_namespace AS n ON n.oid = c.relnamespace
                WHERE n.nspname = 'public' AND c.relkind = 'r'
                ORDER BY c.relname
                """
            )
        ).scalars()
        for name in names:
            _check_ident(name)
            counts[name] = int(
                connection.execute(text(f'SELECT count(*) FROM public."{name}"')).scalar_one()
            )
    return counts


def run_synthetic_drill(work_dir: Path) -> RestoreDrillResult:
    """Dump and restore synthetic rows. Raises when Postgres tools are missing.

    Callers that should skip, including pytest, check ``locate_postgres_binaries``
    first. This function itself fails closed so a missing tool is not a pass.
    """
    binaries = locate_postgres_binaries()
    if binaries is None:
        raise PostgresUnavailable(
            "PostgreSQL binaries initdb, pg_ctl, pg_dump, and pg_restore were not found"
        )
    work_dir.mkdir(parents=True, exist_ok=True)
    with _ephemeral_cluster(work_dir, binaries) as cluster:
        _create_database(cluster, SOURCE_DATABASE)
        _create_database(cluster, RESTORE_DATABASE)
        source = cluster.engine(SOURCE_DATABASE)
        restored = cluster.engine(RESTORE_DATABASE)
        try:
            seed_synthetic(source)
            source_counts = table_counts(source)
            dump_path = work_dir / "synthetic-restore-drill.dump"
            _dump_database(cluster, SOURCE_DATABASE, dump_path)
            header = dump_path.read_bytes()[:5]
            if header != b"PGDMP":
                raise RuntimeError("pg_dump did not write a custom-format archive")
            _restore_database(cluster, RESTORE_DATABASE, dump_path)
            restored_counts = table_counts(restored)
        finally:
            source.dispose()
            restored.dispose()
    return RestoreDrillResult(
        source_counts=source_counts,
        restored_counts=restored_counts,
        dump_path=dump_path,
    )


def seed_synthetic(engine: Engine) -> None:
    """Insert one clearly fake firm and the rows that hang off it.

    Addresses use example.com. The storage path is a synthetic URI, not an
    S3 or Egnyte location. No document body is stored.
    """
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        firm = Firm(name="Synthetic Restore Drill BD", slug="synthetic-restore-drill")
        session.add(firm)
        session.flush()
        auditor = User(
            email="restore-drill-auditor@example.com",
            name="Synthetic Auditor",
            role=UserRole.AUDITOR,
        )
        client = User(
            firm_id=firm.id,
            email="restore-drill-client@example.com",
            name="Synthetic Client",
            role=UserRole.CLIENT,
        )
        session.add_all([auditor, client])
        session.flush()
        engagement = Engagement(
            firm_id=firm.id,
            auditor_id=auditor.id,
            review_period_start=date(2024, 1, 1),
            review_period_end=date(2024, 12, 31),
            due_date=date(2025, 3, 31),
        )
        session.add(engagement)
        session.flush()
        policy = ChecklistItemInstance(
            firm_id=firm.id,
            engagement_id=engagement.id,
            item_key="synthetic-policy",
            section_key="synthetic",
            section_title="Synthetic section",
            title="Synthetic AML policy",
            description="Mock checklist row for the backup restore drill.",
            position=1,
        )
        training = ChecklistItemInstance(
            firm_id=firm.id,
            engagement_id=engagement.id,
            item_key="synthetic-training",
            section_key="synthetic",
            section_title="Synthetic section",
            title="Synthetic training roster",
            description="Second mock checklist row so the drill count is not one everywhere.",
            position=2,
        )
        session.add_all([policy, training])
        session.flush()
        session.add(
            Document(
                firm_id=firm.id,
                item_instance_id=policy.id,
                uploaded_by_id=client.id,
                original_name="synthetic-policy.txt",
                content_type="text/plain",
                size_bytes=32,
                egnyte_path="synthetic://restore-drill/synthetic-policy.txt",
                sha256="ab" * 32,
            )
        )
        session.add(
            AuditLog(
                firm_id=firm.id,
                actor_id=auditor.id,
                action="synthetic.restore_drill",
                entity_type="engagement",
                entity_id=engagement.id,
                previous_hash=app.audit.GENESIS,
                details={"source": "synthetic-restore-drill"},
            )
        )
        session.commit()


def format_counts(result: RestoreDrillResult) -> str:
    names = sorted(set(result.source_counts) | set(result.restored_counts))
    width = max([len("table"), *(len(name) for name in names)])
    lines = [f"{'table':<{width}}  {'source':>8}  {'restored':>8}"]
    for name in names:
        left = result.source_counts.get(name)
        right = result.restored_counts.get(name)
        lines.append(f"{name:<{width}}  {_cell(left):>8}  {_cell(right):>8}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if args in (["-h"], ["--help"]):
        print(__doc__.strip())
        return 0
    if args:
        print(
            "scripts/backup_restore.py accepts no arguments. "
            "It seeds synthetic rows on a private cluster. "
            "Fetch and restore production dumps by following docs/backup-restore.md.",
            file=sys.stderr,
        )
        return 2
    if locate_postgres_binaries() is None:
        print(
            "PostgreSQL binaries initdb, pg_ctl, pg_dump, and pg_restore were not found. "
            "Install the PostgreSQL server packages and retry.",
            file=sys.stderr,
        )
        return 2
    with tempfile.TemporaryDirectory(prefix="ains-backup-restore-") as directory:
        result = run_synthetic_drill(Path(directory))
        print(format_counts(result))
        mismatches = compare_counts(result.source_counts, result.restored_counts)
        if mismatches:
            for line in mismatches:
                print(line, file=sys.stderr)
            return 1
        for name, expected in SEEDED_COUNTS.items():
            actual = result.source_counts.get(name)
            if actual != expected:
                print(f"seed count drift: {name}={actual} expected={expected}", file=sys.stderr)
                return 1
        print(f"OK: {len(result.source_counts)} tables match")
        return 0


def _cell(value: int | None) -> str:
    return "-" if value is None else str(value)


def _check_ident(name: str) -> None:
    if not _IDENT.fullmatch(name):
        raise ValueError(f"Refusing unexpected SQL identifier {name!r}")


def _pg_env() -> dict[str, str]:
    env = os.environ.copy()
    for key in ("PGHOST", "PGPORT", "PGUSER", "PGPASSWORD", "PGDATABASE", "DATABASE_URL"):
        env.pop(key, None)
    return env


def _run(args: list[str], *, timeout: int = 120, log_path: Path | None = None) -> None:
    try:
        completed = subprocess.run(
            args,
            check=False,
            capture_output=True,
            timeout=timeout,
            env=_pg_env(),
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"{Path(args[0]).name} timed out after {timeout}s") from exc
    if completed.returncode != 0:
        detail = completed.stderr.decode("utf-8", errors="replace").strip()
        if log_path is not None and log_path.is_file():
            tail = log_path.read_text(encoding="utf-8", errors="replace")[-4000:]
            detail = f"{detail}\n{tail}".strip()
        raise RuntimeError(f"{Path(args[0]).name} failed ({completed.returncode}): {detail}")


@contextmanager
def _ephemeral_cluster(work_dir: Path, binaries: PostgresBinaries) -> Iterator[_Cluster]:
    data_dir = work_dir / "pgdata"
    socket_dir = work_dir / "socket"
    socket_dir.mkdir(mode=0o700)
    log_path = work_dir / "postgres.log"
    with socket.socket() as available:
        available.bind(("127.0.0.1", 0))
        port = int(available.getsockname()[1])
    _run(
        [
            str(binaries.initdb),
            "-D",
            str(data_dir),
            "-A",
            "trust",
            "-U",
            CLUSTER_USER,
            "--locale=C",
            "--encoding=UTF8",
        ]
    )
    _run(
        [
            str(binaries.pg_ctl),
            "-D",
            str(data_dir),
            "-l",
            str(log_path),
            "-o",
            f"-k {socket_dir} -p {port} -c listen_addresses=''",
            "-w",
            "start",
        ],
        log_path=log_path,
    )
    cluster = _Cluster(
        binaries=binaries, data_dir=data_dir, socket_dir=socket_dir, port=port
    )
    try:
        yield cluster
    finally:
        _run(
            [str(binaries.pg_ctl), "-D", str(data_dir), "-m", "immediate", "stop"],
            timeout=60,
        )


def _create_database(cluster: _Cluster, name: str) -> None:
    _check_ident(name)
    admin = cluster.engine("postgres")
    try:
        with admin.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
            connection.execute(text(f'CREATE DATABASE "{name}"'))
    finally:
        admin.dispose()


def _dump_database(cluster: _Cluster, database: str, destination: Path) -> None:
    _check_ident(database)
    _run(
        [
            str(cluster.binaries.pg_dump),
            "--format=custom",
            "--no-password",
            "-h",
            str(cluster.socket_dir),
            "-p",
            str(cluster.port),
            "-U",
            CLUSTER_USER,
            "-d",
            database,
            "-f",
            str(destination),
        ]
    )


def _restore_database(cluster: _Cluster, database: str, dump_path: Path) -> None:
    _check_ident(database)
    _run(
        [
            str(cluster.binaries.pg_restore),
            "--exit-on-error",
            "--single-transaction",
            "--no-owner",
            "--no-acl",
            "--no-password",
            "-h",
            str(cluster.socket_dir),
            "-p",
            str(cluster.port),
            "-U",
            CLUSTER_USER,
            "-d",
            database,
            str(dump_path),
        ]
    )


if __name__ == "__main__":
    raise SystemExit(main())
