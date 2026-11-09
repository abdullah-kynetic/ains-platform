# TEST-2 results on candidate b2cd6ae (claude/impl-security)
Bundle sha256 verified OK. Environment: sandbox, root, PG 16.15 (apt), restic 0.16.4 + rclone 1.60.1 (apt worked here, contrary to VERIFY-1), S3 = moto emulator (MinIO download 403 via proxy x3, so BLOCKED; label: EMULATOR, not MinIO, not R2). Docker unavailable: `docker` is replaced by tests/drill/shim/docker (not Docker coverage).

| Check | Result | Evidence |
|---|---|---|
| ruff + full pytest incl. 5 PG tests, non-root | PASS: 316 passed, 1 skipped | run on b2cd6ae |
| Backup/restore drill (27 checks) | 26 PASS, 1 FAIL (defect D1) | drill-results-b2cd6ae.tsv, harness tests/drill/run_drill.sh on branch claude/project-thread-u84amq |
| Real PG sign-in lockout, concurrent first failures | FAIL (defect D2) | patches/test_signin_lockout_postgres.py |
| bash -n all deploy scripts, shellcheck warnings | PASS (only SC1090 info) | |
| compose YAML parses | PASS (parse only; `docker compose config` NOT RUN) | |
| Docker build, Caddy validate, systemd runtime, lock-drill (needs R2 object lock), real R2, ClamAV, live OpenRouter | NOT RUN / out of scope | |

## Defects
D1 backup.sh: if pg_dump fails the pipe still lets `restic backup --stdin` save a snapshot (tagged db) of the partial/empty dump; script exits nonzero but `restore.sh latest` then restores a bad dump. Repro: DRILL_SRC_DB=no_such_db backup.sh -> db snapshots 1 -> 2. Fix: dump to a temp file, verify with `pg_restore -l` and size > 0, then `restic backup`; (IMPL-2 reportedly fixing).
D2 app/auth/lockout.py: SELECT FOR UPDATE on a missing row locks nothing, so concurrent first failures both INSERT the same key; one raises IntegrityError -> HTTP 500 (observed on PG16: [401 x7, IntegrityError]) and counts can be lost. Fix: INSERT .. ON CONFLICT DO NOTHING (or catch IntegrityError and retry) before the locked read / atomic UPDATE count=count+1. Test fails until fixed (fails 3 of 4, race dependent).
Notes (non-defects): restore-drill.sh verifies only one document (first by id) plus row counts; PG re-deparses CHECK text on restore (harness compares names only); drill depends on the app being quiescent (row-count drift fails by design).
