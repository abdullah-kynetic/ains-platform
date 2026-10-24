"""Dump, restore, and compare row counts on a private synthetic Postgres cluster.

Skipped when initdb, pg_ctl, pg_dump, and pg_restore are not installed together.
The drill never reads S3, DATABASE_URL, or a production dump.
"""

from pathlib import Path

import pytest

from app.database.models import Base
from scripts.backup_restore import (
    SEEDED_COUNTS,
    compare_counts,
    locate_postgres_binaries,
    main,
    run_synthetic_drill,
)

pytestmark_postgres = pytest.mark.skipif(
    locate_postgres_binaries() is None,
    reason="Local Postgres binaries are needed for the backup restore drill",
)


def test_compare_counts_reports_each_difference() -> None:
    assert compare_counts(
        {"firms": 1, "users": 2, "documents": 0},
        {"firms": 1, "users": 1, "audit_logs": 3},
    ) == [
        "audit_logs: source=None restored=3",
        "documents: source=0 restored=None",
        "users: source=2 restored=1",
    ]


def test_compare_counts_is_empty_when_tables_match() -> None:
    assert compare_counts({"firms": 1, "users": 0}, {"users": 0, "firms": 1}) == []


def test_cli_help_does_not_start_postgres(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--help"]) == 0
    captured = capsys.readouterr()
    assert "synthetic" in captured.out.lower()
    assert captured.err == ""


def test_cli_rejects_dump_and_s3_arguments(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--dump", "s3://example/backups/ains-20260115T093000Z.dump"]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "docs/backup-restore.md" in captured.err


@pytestmark_postgres
def test_synthetic_dump_restore_matches_table_counts(tmp_path: Path) -> None:
    result = run_synthetic_drill(tmp_path)
    assert result.source_counts == result.restored_counts
    assert set(result.source_counts) == set(Base.metadata.tables)
    for table_name, expected in SEEDED_COUNTS.items():
        assert result.source_counts[table_name] == expected
    assert result.source_counts["finding_drafts"] == 0
    assert result.source_counts["check_jobs"] == 0
    assert result.source_counts["mfa_recovery_codes"] == 0
    assert result.dump_path.is_file()
    assert result.dump_path.read_bytes().startswith(b"PGDMP")
    assert sum(result.source_counts.values()) == sum(SEEDED_COUNTS.values())


@pytestmark_postgres
def test_cli_synthetic_drill_exits_zero(capsys: pytest.CaptureFixture[str]) -> None:
    assert main([]) == 0
    captured = capsys.readouterr()
    assert "OK:" in captured.out
    assert "firms" in captured.out
    assert captured.err == ""
