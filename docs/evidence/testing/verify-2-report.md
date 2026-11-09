# VERIFY-2 report: claude/impl-security-2 @ 89d925f585bf2b221c3e1c7f621f5716f727f1c3

Bundle SHA256 matched its .sha256. Base main 87783af. Environment: sandbox, Python 3.12.3, PostgreSQL 16.15 as user `postgres`, no Docker/restic/rclone. Synthetic data only. No code fixed.
Probe scripts (scratch, not committed): /mnt/project-files/testing/verify-probes/ (test_probe.py second auditor sweep, test_probe2.py lockout, test_probe3.py responses-requested canaries). Run with PYTHONPATH=. from the repo root.

## Checks
| Check | Result |
|---|---|
| ruff | PASS |
| Suite excluding the 6 PG files | PASS: 336 passed, 1 skipped (SQLite API tests) |
| PG files as non-root on PostgreSQL 16.15 (5 original + 6 lockout) | PASS: 11 passed, 0 skipped |
| Probe: second unassigned auditor vs all auditor routes | PASS, no leaks |
| Probe: responses-requested canaries | PASS (below) |
| Deploy scripts | `bash -n` earlier PASS; restore-drill awk window logic exercised on synthetic counts: PASS (ok, high, missing, extra table). Real restic/rclone/Docker run: BLOCKED |
| Real ClamAV, live OpenRouter, Docker/compose | NOT RUN |

## Previous defects
- D1 FIXED (config): ENV=production + UPLOAD_SCAN_MODE=clamav set in the api service, clamav service added, app refuses to start with scanning off in production. Mutation (guard disabled) killed by tests. Real clamd NOT RUN.
- D2 FIXED: M1 (drop assignment filter, auditor.py:209) now killed by tests/test_auditor_assignment.py.
- D3 FIXED, with residual: lockout now keyed by email+address pair (5), email total (50), address (30). Mutation reverting to email-only killed by 2 tests. Residual: a distributed attacker can still lock an account after 50 failures.
- D4 FIXED: probe shows 7 correct-password requests without code no longer lock; valid login then 200. Mutation killed.
- D5 FIXED: 6 new PG lockout tests, including concurrent first failures. Mutation disabling the race-safe insert is killed on PostgreSQL (3 failures) and, as expected, not on SQLite.
- D6 IMPLEMENTED, see below.
- D7 FIXED in script, execution BLOCKED: dump to work file, validated (non-empty, pg_restore --list, has TABLE DATA) before restic, tagged `validated`; config snapshots thinned; drill compares against counts recorded at backup time; README documents off-server keys. Never run against real restic.
- D8 FIXED: daily cap and error counter persisted (SQLite/PG, atomic UPDATE); every listed price must be exactly zero (Decimal, fail closed). Live OpenRouter param names still unverified.

## Responses requested (D6)
Endpoints: POST release and withdraw (auditor, assigned only), GET /engagements/{id}/responses-requested (client). Response is a typed model: itemId, title, requestText only.
Probe result: released item returns exactly those three fields. Unreleased item, other-firm item with released text, restricted item with released text, and all internal canaries (finding, task, note, draft report) absent. Not present in /engagements/current. Other-firm GET 404. Client release attempt 403. Audit log stores text length only.
Mutations: dropping the restricted filter was caught. Dropping the engagement/firm filter on the GET was NOT caught (N1).

## New findings
N1 (Medium, test gap) app/api/intake.py GET responses-requested: removing the `engagement_id` and `firm_id` conditions from the query leaves all 8 tests green. Under that mutation a client would receive released requests from every engagement and firm. Code is correct today. Needs a test that releases an item in another engagement and another firm and asserts it is absent (probe test_probe3.py does this and passes on the real code).
N2 (Low) withdraw does not clear response_request_text in the database if the line is removed (mutation survived); the GET hides it because released_at is also required. Withdrawn text currently is cleared in the real code; only the test is weak.
N3 (Low) clamav: api now depends on clamav being healthy (180 s start period, 1.3 GB limit); image not pinned by digest; CLAMD_CONF_* env names and StreamMaxLength 100M are unverified without running the image. Fail-closed by design.
N4 (Low) Changed migration tests (client_profiles, monday, deployment_migration) only adapt to the new a117 head and drop the new columns before replaying; reviewed, not weakened.

## Verdict
All of D1 to D8 are fixed in code and covered by tests that catch their mutations, except real-environment behaviour (ClamAV, restic/rclone, live OpenRouter, compose) which stays BLOCKED/NOT RUN. N1 is the one test gap worth closing before the "cloud implementation verified" label.
