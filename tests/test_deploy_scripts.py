"""Run the backup and alert scripts against stub docker/restic/curl binaries (no real services)."""

import os
import stat
import subprocess
from pathlib import Path

import pytest

ROOT = Path.cwd()


def _stub(bin_dir: Path, name: str, body: str) -> None:
    path = bin_dir / name
    path.write_text("#!/bin/sh\n" + body)
    path.chmod(path.stat().st_mode | stat.S_IEXEC)


@pytest.fixture
def sandbox(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log = tmp_path / "calls.log"
    _stub(
        bin_dir,
        "docker",
        'echo "docker $*" >> "$STUB_LOG";'
        ' case "$*" in'
        ' *pg_dump*) echo PGDMP-partial; [ -n "$STUB_DUMP_FAIL" ] && exit 1; exit 0;;'
        ' *pg_restore*) cat >/dev/null; [ -n "$STUB_BAD_TOC" ] || echo "; TABLE DATA public users";'
        ' [ -n "$STUB_BAD_TOC" ] && echo "; empty"; exit 0;;'
        ' *) echo "users=3"; exit 0;; esac',
    )
    _stub(
        bin_dir,
        "restic",
        'echo "restic $*" >> "$STUB_LOG"; cat > /dev/null;'
        ' [ -n "$STUB_RESTIC_FAIL" ] && exit 1; exit 0',
    )
    _stub(
        bin_dir,
        "curl",
        'for a; do last=$a; done; echo "curl $last" >> "$STUB_LOG"',
    )
    env_file = tmp_path / "restic.env"
    env_file.write_text(
        "RESTIC_REPOSITORY=s3:stub\nHEALTHCHECK_PING_URL=https://ping.invalid/abc\n"
    )
    env = {
        "PATH": f"{bin_dir}:/usr/bin:/bin",
        "STUB_LOG": str(log),
        "RESTIC_ENV_FILE": str(env_file),
        "KIEN_ENV_FILE": str(tmp_path / "kien.env"),
        "KIEN_BACKUP_WORK": str(tmp_path / "work"),
    }
    return env, log


def _run(script: str, env: dict, *args: str, **extra) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["bash", str(ROOT / script), *args], env={**env, **extra}, capture_output=True, text=True
    )


def test_backup_pings_success_only_after_everything_ran(sandbox):
    env, log = sandbox
    result = _run("deploy/backup/backup.sh", env)
    assert result.returncode == 0, result.stderr
    calls = log.read_text().splitlines()
    assert any("kien-db.dump" in c and "--tag db --tag validated" in c for c in calls)
    assert any("kien-db.counts.before" in c and "kien-db.counts.after" in c for c in calls)
    assert any("pg_restore --list" in c for c in calls)  # validated before the snapshot
    assert not (tmp_path_work(env)).exists()  # work files removed
    assert any("backup /opt/kien/deploy /etc/kien --tag config" in c for c in calls)
    assert any(
        "forget --tag db --keep-daily 14 --keep-weekly 8 --keep-monthly 6" in c for c in calls
    )
    assert calls[-1] == "curl https://ping.invalid/abc"


def tmp_path_work(env):
    return Path(env["KIEN_BACKUP_WORK"])


def test_truncated_or_invalid_dump_never_becomes_a_db_snapshot(sandbox):
    for failing in ("STUB_DUMP_FAIL", "STUB_BAD_TOC"):
        env, log = sandbox
        log.write_text("")
        result = _run("deploy/backup/backup.sh", env, **{failing: "1"})
        assert result.returncode != 0, failing
        calls = log.read_text().splitlines()
        assert not any(c.startswith("restic backup") and "--tag db" in c for c in calls), failing
        assert calls[-1] == "curl https://ping.invalid/abc/fail", failing


@pytest.mark.parametrize("failing", ["STUB_RESTIC_FAIL", "STUB_DUMP_FAIL"])
def test_backup_failure_pings_fail_and_never_success(sandbox, failing):
    env, log = sandbox
    result = _run("deploy/backup/backup.sh", env, **{failing: "1"})
    assert result.returncode != 0
    pings = [c for c in log.read_text().splitlines() if c.startswith("curl")]
    assert pings == ["curl https://ping.invalid/abc/fail"]


def test_restore_refuses_live_database_container(sandbox):
    env, log = sandbox
    result = _run("deploy/backup/restore.sh", env, "latest", "kien-postgres-1", "u", "d")
    assert result.returncode == 3
    assert not log.exists() or "restic" not in log.read_text()


def test_disk_alert_pages_at_85_percent(sandbox, tmp_path):
    env, _ = sandbox
    fake_df = tmp_path / "fake_df.sh"
    fake_df.write_text("#!/bin/sh\necho 'Use%'\necho ' 90%'\n")
    fake_df.chmod(0o755)
    result = _run("deploy/ops/disk-alert.sh", env, DF_CMD=str(fake_df))
    assert "ALERT[page] disk / at 90%" in result.stderr
    assert result.returncode == 2


def test_scripts_contain_no_literal_secrets_and_units_reference_real_scripts():
    for path in list(Path("deploy").rglob("*.sh")) + list(Path("deploy").rglob("*.example")):
        text = path.read_text()
        assert "AKIA" not in text and "BEGIN PRIVATE KEY" not in text
    for unit in Path("deploy/systemd").glob("*.service"):
        for line in unit.read_text().splitlines():
            if line.startswith("ExecStart=/opt/kien/"):
                for token in line.split():
                    if token.startswith("/opt/kien/"):
                        assert (Path.cwd() / token.removeprefix("/opt/kien/")).exists(), token
    assert os.access("deploy/backup/backup.sh", os.X_OK)


def test_backup_refuses_an_unsafe_work_directory(sandbox):
    env, log = sandbox
    result = _run("deploy/backup/backup.sh", env, KIEN_BACKUP_WORK="/etc")
    assert result.returncode == 2
    assert "restic" not in (log.read_text() if log.exists() else "")


def test_drill_compares_against_backup_time_counts_not_live_database():
    text = Path("deploy/backup/restore-drill.sh").read_text()
    assert "kien-db.counts.before" in text and "kien-db.counts.after" in text
    assert "src=$(kien_compose" not in text  # no comparison with the live database
    readme = Path("deploy/backup/README.md").read_text()
    assert "off the server" in readme and "restic password" in readme.lower()


def test_restore_drill_creates_its_temp_dir_after_the_first_cleanup():
    lines = Path("deploy/backup/restore-drill.sh").read_text().splitlines()
    first_cleanup = lines.index("cleanup")
    mktemp = next(i for i, line in enumerate(lines) if line.startswith("SCRATCH_TMP=$(mktemp"))
    assert mktemp > first_cleanup  # cleanup() must not delete the dir the drill is about to use
    assert any('rm -rf "${SCRATCH_TMP:-}"' in line for line in lines)
