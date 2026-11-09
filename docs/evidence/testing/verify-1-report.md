# VERIFY-1 report: claude/impl-security @ b2cd6aef9938e1d50b59f3b6655182285e1cfa90

Base: main 87783af. Bundle SHA256 4bb1689d...afaf matched its .sha256 file.
Environment: sandbox, Python 3.12.3, PostgreSQL 16.15 (local packages, run as user `postgres`), no Docker, no restic/rclone/shellcheck (apt cannot locate them).
Synthetic data only. No code fixed. Probe scripts lived outside the repo (scratch dir) and are not committed.

## Checks

| # | Check | Command | Result |
|---|---|---|---|
| 1 | Bundle integrity | `sha256sum` vs .sha256 | PASS |
| 2 | Lint | `uv run ruff check .` | PASS |
| 3 | Suite excluding PG files | `uv run pytest -q --ignore=<4 PG files>` | PASS: 311 passed, 1 skipped (SQLite in-memory for API tests) |
| 4 | Five PG tests, real PostgreSQL 16.15, non-root | `runuser -u postgres -- ... pytest tests/test_{audit,invoice,monday,client_profiles}_postgres.py` | PASS: 5 passed, 0 skipped |
| 5 | Unassigned second auditor vs all 42 auditor routes (own probe, real engagement/report/task ids) | scratch probe | PASS: item/engagement/report/task/invoice-scoped routes 404, no marker leaks. Finding and invoice routes only hit with fake ids, so they were reviewed by reading (assignment filter present at app/api/auditor.py:209) |
| 6 | Client payload allowlist / no findings, notes, tasks, reports | tests/test_client_view_allowlist.py, test_route_isolation.py | PASS (SQLite) |
| 7 | Response-request items expose only released titles and request text | grep app/ | NOT RUN: no backend implementation exists (only frontend mock) |
| 8 | Sign-in lockout, recovery | tests/test_signin_lockout.py + probes | PASS with defects D3, D4 |
| 9 | Upload scanning, quarantine, fail-closed | tests/test_upload_scanning.py | MOCKED: fake clamd speaking INSTREAM. Logic PASS; real ClamAV NOT RUN. Deployment gap D1 |
| 10 | Rate limits and recovery | tests/test_rate_limit.py | PASS (unit, in-process) |
| 11 | OpenRouter free-only guard | tests/test_ai_adapter.py | MOCKED (respx). Live OpenRouter NOT RUN. Param names are marked [Verify] in code |
| 12 | Mutation checks (my copy only) | see below | 4 of 5 killed, 1 survived (D2) |
| 13 | Deploy/backup scripts | `bash -n` on all | PASS syntax only. Execution BLOCKED (no restic/rclone/Docker) |
| 14 | Backup/restore round trip | n/a | BLOCKED |

Mutations: removing lockout counting, making scan failure fail open, disabling the rate limit, and removing the magic-link lock check were each caught by a test. Removing the assignment filter on PATCH /auditor/findings/{id} was NOT caught (268 passed).

## Defects

D1 (High) Scanning is off by default and the production stack has no scanner. app/config.py:52 defaults `upload_scan_mode="off"`; deploy/docker-compose.prod.yml has no clamd service and no scan variable; nothing refuses to start in production with scanning off. If /etc/kien/kien.env omits UPLOAD_SCAN_MODE, uploads go unscanned silently. Repro: grep -in clam deploy/docker-compose.prod.yml returns nothing.

D2 (Medium, test gap) No test covers cross-assignment on finding or invoice routes. tests/test_route_isolation.py fills unknown path ids with "unknown-id" so a 404 passes for any reason. Mutation M1 (delete `Engagement.auditor_id == user.id` at app/api/auditor.py:209) leaves all tests green. The code is currently correct.

D3 (Medium, design) Anyone can lock a known account. Lockout is keyed by email alone (app/auth/lockout.py). Repro: 5 wrong passwords for alpha-client@example.test, then the correct password returns 429 with Retry-After 900. Repeatable every 15 minutes. Coordinator decision: key by email+address, or add backoff.

D4 (Low) A correct password with a missing MFA code returns 401 and counts as a failure (app/auth/router.py:195-199). Repro: 5 requests with correct password and no code, then a valid login with a good code returns 429.

D5 (Medium, test adequacy) All API tests run on SQLite (tests/test_backend_api.py:109), so `with_for_update` row locking in app/auth/lockout.py:39,68 and concurrent first-failure behaviour are untested. Only the 5 PG tests touch PostgreSQL. Concurrent first failures on a new key may raise an integrity error (inferred, not reproduced).

D6 (Medium, requirement gap) Response-request release (released titles plus auditor request text only) has no backend implementation or tests, so that requirement is unverified. The client payload does include `followUp` and `reason` fields; confirm they carry no auditor-internal text once the feature is built.

D7 (Medium, inferred, not run) deploy/backup/backup.sh:15: if pg_dump dies mid-stream, restic can still commit a truncated `kien-db.dump` snapshot tagged `db`, which later reads as "latest". The restic password file lives in /etc/kien, which is also what is lost in a server loss, so confirm it is stored off-server. restore-drill.sh compares live row counts and will fail whenever writes occurred after the backup. Config snapshots are never forgotten.

D8 (Low) AI adapter: price check covers only four price fields; the daily cap and error counter are in memory and reset on restart; SAR gating trusts caller-supplied `source` and `tags` plus the checklist item id, not content; the post-check runs after the call. Zip-bomb check trusts declared sizes.

D9 (Low, NOT RUN) Per-address limits depend on `--forwarded-allow-ips=172.30.0.2` matching Caddy's pinned address. Both are present in the compose file (PASS by reading) but not exercised, because there is no Docker here.

## Not verified
Real R2, real ClamAV, live OpenRouter, Docker build and compose, Caddy config, restic/rclone, deployed preview. All explicitly deferred or blocked.

## Verdict
Candidate passes everything that ran, but D1 and D6 block "cloud implementation verified" for scanning and response-request release, and D2/D5 weaken the evidence. Backup/restore remains BLOCKED until restic and rclone can be installed in a disposable environment.
