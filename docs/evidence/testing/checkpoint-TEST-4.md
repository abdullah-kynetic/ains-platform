# TEST-4 final regression: claude/impl-security-2 @ b6de342 (bundle SHA256 OK)
Env: sandbox, PG 16.15 (apt), PG tests as non-root; restic 0.16.4, rclone 1.60.1; S3 = moto EMULATOR (not MinIO/real R2); `docker` = shim (not Docker). Harness tests/drill/run_drill.sh @ claude/project-thread-u84amq (5c89d85). No patches applied.
| Check | Result |
|---|---|
| ruff check . | PASS |
| Full pytest incl. all PG files, non-root, real PG 16.15 | PASS: 350 passed, 1 skipped |
| Lockout PG tests (test_lockout_postgres + test_signin_lockout_postgres, 6 tests) x12 | PASS 12/12 |
| Drill as shipped | PASS 27/27 (drill-results-b6de342.tsv); D9 fixed, no partial snapshot, restore/app reads/checksums/encryption/error handling all pass |
NOT RUN: Docker build/compose config, Caddy, systemd runtime, R2 object-lock lock-drill, real R2, real ClamAV, live OpenRouter, VPS/deployed preview. Pre-existing: ruff format would reformat files on main too (not a gate).
