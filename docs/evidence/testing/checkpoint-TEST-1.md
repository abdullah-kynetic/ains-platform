# TEST-1 checkpoint (testing worker)
Updated 2026-11-07. Input commit: 87783af5a820e04b255bcbb419d6ed89393aa764 (main, merge of #77). Owner: this thread.

## Environment
Real PostgreSQL 16.15 (Ubuntu apt, /usr/lib/postgresql/16), disposable cluster per test via initdb in tmp dir. Docker daemon unavailable here. Key finding: initdb refuses to run as root, which is why the five DB tests "failed" earlier; run pytest as a non-root user (pgtest), TMPDIR on a writable dir.
Also needs a writable repo copy and a readable CA bundle copy; helper: tests/run_as_nonroot.sh
Command: su pgtest -c "TMPDIR=/tmp/pgt .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_audit_postgres.py tests/test_invoice_postgres.py tests/test_monday_postgres.py tests/test_client_profiles_postgres.py"

## Results
| Check | Commit | Env | Result |
|---|---|---|---|
| 5 DB tests: audit backfill trigger + concurrent appends, unassigned document migration, invoice migration + concurrent numbering, monday additive schema, client profile upgrade/downgrade | 87783af5a820e04b255bcbb419d6ed89393aa764 | real PG 16.15 | PASS (5 passed) |
| Full suite | 87783af | real PG 16.15, non-root, repo copy | PASS (224 passed, 1 skipped); ruff PASS |
| Backup/restore/deploy scripts review + drill | n/a | n/a | BLOCKED: scripts are in six unpushed local branches of the build thread (push card pending) |


## Open
- Waiting for impl commits to be reachable, then rerun on that SHA.
- Next: build MinIO/local-storage + PG backup/restore drill harness, run against scripts once pushed.
