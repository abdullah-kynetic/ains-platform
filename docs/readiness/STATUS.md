# Readiness tracker (all 45 items)

Source list: [`readiness-checklist-2026-11-07.md`](readiness-checklist-2026-11-07.md).
Maintained by Lane 2. **Done** means evidence exists in the repo or in a merged PR and was actually run.
**Partial** means some of the item is built. **Open** means not started or not ours. **Blocked** needs a
decision from the named owner. Nothing here claims a live check (R2, ClamAV, email, VPS) that was not run.
Last updated 2026-11-11. Synthetic data only until items 1, 2, 7, 31, 32, 37 and G1/G2 are all closed.

| # | Owner | Status | Evidence or what is missing |
| --- | --- | --- | --- |
| 1 | Abdullah | Open | Written decision on real client data not given. Mock only. |
| 2 | Abdullah | Open | Not confirmed in writing. Code side: no model calls in `app/` (`tests/test_workflow_boundary.py`). |
| 3 | Abdullah | Open | No security or product owner named. |
| 4 | Abdullah | Partial | Code default `RECORD_RETENTION_DAYS=2190` is a placeholder; rules and acceptable data loss not decided. [`kb/31`](../kb/31-retention-export-erasure.md) |
| 5 | Abdullah | Open | No budget cap set. |
| 6 | Attorney | Open | Engagement terms not provided. |
| 7 | Attorney | Open | Verbal only. Written approval not on file. |
| 8 | Quentin, Abdullah | Open | Client consent wording and records not produced. |
| 9 | Abdullah | Open | Insurance status unverified. |
| 10 | Attorney | Open | Decision on moving past client files not given. |
| 11 | Attorney | Open | Chatbot wording not provided. |
| 12 | Claude | Done | `AUTH_REMOVED` no longer exists in `web/src`; real routes `/auth/*` (IMPL-4). Auth tests: `tests/security/test_sessions.py`, `tests/security/test_email_codes.py` (emailed code replaced TOTP, 11 Nov). |
| 13 | Abdullah, Claude | Blocked | VPS size and SSH key from Abdullah; VPS, DNS and OVH stay on hold. Lane C owns the server. Not started. |
| 14 | Claude | Partial | Upload scanning code and tests: `tests/test_upload_scanning.py`, `tests/security/test_upload_controls.py` (`UPLOAD_SCAN_MODE=clamav`, scan failure blocks upload). No live ClamAV run claimed. |
| 15 | Claude | Done | `tests/test_rate_limit.py`, `tests/security/test_rate_limits.py`, `tests/test_signin_lockout.py` (Postgres variant runs in CI). |
| 16 | Claude, Abdullah | Open | No backup script or restore drill in the repo. Needs the VPS and Abdullah's keys. |
| 17 | Claude | Partial | R2 compatibility handled in `app/storage/s3.py` and the R2 version-id fix (PR #116); `scripts/r2_smoke.py` exists. No live R2 run claimed. |
| 18 | Claude | Partial | Secrets are `SecretStr` and only loaded in `app/config.py` (#102, #104); `tests/security/test_no_secrets_in_public_env.py`. Written rotation steps are missing. |
| 19 | Claude | Partial | `tests/security/test_log_scrubbing.py` covers scrubbing in code. The deployed Sentry and log setup is not checked. |
| 20 | Claude, Abdullah | Open | No incident process or one-page runbook yet (`kb/13` is the OVH ops runbook). |
| 21 | Claude | Open | No external checkpoint for the audit chain. Chain itself is tested: `tests/security/test_audit_chain.py`. |
| 22 | Abdullah | Open | SOC 2 groundwork not started. Never claim certification. |
| 23 | Claude | Partial | Practices and practice-scoped routes exist (migration a121, [`kb/24`](../kb/24-practice-api.md)); `practice_scope` denial cases in `tests/security/tenant_denial_cases.txt`. Not yet tested with a real second practice on Postgres. |
| 24 | Claude | Done | Every route has a denial case (`tests/security/tenant_denial_cases.txt`, `test_tenant_isolation.py`, `test_route_isolation.py`, `route_inventory.txt`). Clients never see findings: `tests/security/test_client_fields.py`. |
| 25 | Claude | Partial | Export, plan and erase CLI: `app/retention.py`, `tests/test_storage_retention.py`, [`kb/31`](../kb/31-retention-export-erasure.md). Retention numbers are placeholders (item 4); not run against live storage. |
| 26 | Quentin | Open | Rubric fields stay empty by design. |
| 27 | Quentin | Open | Template wording and sign-off type not confirmed. Current flow is typed-name plus SHA-256 fingerprint ([`kb/28`](../kb/28-signoff-api.md)). |
| 28 | Claude | Partial | Invoices, mark-paid and client invoice list built ([`kb/30`](../kb/30-client-invoices-api.md)). Cards parked until Abdullah picks a provider; reminder emails not built. |
| 29 | Abdullah | Open | No yes/no. Existing `scripts/build_synthetic_firms.py` and `scripts/evaluate_synthetic.py` are not the approved set. |
| 30 | Claude | Partial | `tests/test_end_to_end_flow.py` runs invite to invoice on synthetic data over the API ([`kb/32`](../kb/32-report-confirmation-and-journey.md)). Not a browser run on a deployed build. |
| 31 | Claude | Partial | Last local run: 615 passed, 1 skipped, 12 errors (Postgres tests, no Postgres in the sandbox); ruff clean. CI on the PR is the Postgres proof. Web unit and e2e on a final build not run by Lane 2. |
| 32 | Claude | Partial | Code-level tests: `tests/security/*`, `tests/test_synthetic_uploads.py`, sign-in lockout. Not run against a preview. SAR upload rejection not evidenced (see 40). |
| 33 | Claude | Open | Needs item 16 and a clean box. |
| 34 | Abdullah | Open | Cost decision for an outside tester. |
| 35 | Quentin | Open | No sanitized sample provided. |
| 36 | Quentin, Abdullah | Open | Depends on 1, 8, 37. |
| 37 | Abdullah | Open | Needs VPS, backups and monitoring first. |
| 38 | Abdullah, Quentin | Open | After 36. |
| 39 | Claude | Partial | `tests/test_workflow_boundary.py` passes; adapter lives in frozen `ai_adapter/**`. Logging of model, tokens and cost is Stage 3 work. |
| 40 | Claude | Open | SAR detection before model calls not evidenced in `app/`. Engine work is frozen until G2. AML-BD-017 and 025 are metadata-only, human-only. |
| 41 | Attorney | Blocked | Vendor approval conflicts with CLAUDE.md rule 10. Recorded in [`kb/19`](../kb/19-open-questions.md). Not invented here. |
| 42 | Quentin | Open | Gold set not provided. |
| 43 | Claude | Open | Frozen until G2. Free hosted models only for the trial. |
| 44 | Claude, Quentin | Partial | Findings need a page citation to be accepted (`app/api/auditor.py`, 422 otherwise); only an auditor action approves findings and signs ([`kb/28`](../kb/28-signoff-api.md)). No AI suggestions exist yet. |
| 45 | Claude | Open | Not built. Frozen until G2. |

## Counts

Done: 3 (items 12, 15, 24). Partial: 13. Blocked: 2 (13, 41). Open: 27. Total 45.
Most Open items are owned by Abdullah, Quentin or the attorney.

## What Lane 2 can still do without anyone

Items 18 (rotation steps), 20 (incident one-pager), 21 (checkpoint), 23 (second-practice test) and 28 (reminders)
are doable now. Items 13, 16 and 33 wait on Abdullah and Lane C. Items 39 to 45 wait on G2.
