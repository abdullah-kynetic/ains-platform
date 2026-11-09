# TEST-3 final regression: claude/impl-security-2 @ 89d925f (bundle SHA256 OK)
Env: sandbox, PG 16.15 (apt), non-root for PG tests; restic 0.16.4, rclone 1.60.1; S3 = moto EMULATOR (not MinIO, not real R2); `docker` = shim (tests/drill/shim, not Docker). Harness: tests/drill/run_drill.sh @ branch claude/project-thread-u84amq.

| Check | Result |
|---|---|
| ruff check . | PASS |
| ruff format --check . | PRE-EXISTING: main (87783af) also has 19 files that would be reformatted; not a documented gate, so informational |
| Full pytest, non-root, real PG 16.15 (includes all PG files) | PASS: 347 passed, 1 skipped |
| Lockout PG tests (test_lockout_postgres.py + test_signin_lockout_postgres.py, 6 tests) x12 runs | PASS 12/12 |
| Drill, as shipped | 26 PASS, 1 FAIL: restore_drill (defect D9) |
| Drill with D9 one-line patch (patches/restore-drill-scratch-tmp.patch) | restore_drill PASS; all other checks PASS (27/27 with updated row-drift semantics) |
| backup_no_partial_snapshot (old D1/D7) | PASS (db snapshots 1 -> 1) |

D9 (NEW, shipped candidate): deploy/backup/restore-drill.sh creates SCRATCH_TMP then calls cleanup() (which rm -rf's it) before using it -> "restore-drill.sh: line 31: .../before: No such file or directory", drill exits 1 even when backup is fine. Fix: call cleanup before mktemp (patch attached).
Semantics note: drill now compares to backup-time counts, so writes after backup no longer fail it (harness check renamed drill_ignores_post_backup_writes).
Still NOT RUN: Docker build/compose config, Caddy, systemd runtime, lock-drill (R2 object lock), real R2/ClamAV/OpenRouter, deployed preview.
