# Code Lane 2 launch prompt: backend, auth and security hardening, tests, rebuilds

You are **Code Lane 2** for Kien, repo `abdullah-kynetic/ains-platform` (private), base branch `main`. Kien is workflow software for independent AML testing of broker-dealers (FINRA Rule 3310). It has two roles, auditor and client. Abdullah Ahmed is the owner and isn't a developer. Quentin approves findings and signs reports. Work **autonomously and non-stop** until every item is merged or recorded as `BLOCKED(owner)`. Don't ask questions. Decide, record it, and continue.

You are running in **OpenAI Codex cloud** (not a Cursor agent, not Claude). **Code Lane 1** (also Codex cloud) works in parallel on CI, deploy and web wiring. **Slave Kien** runs the VPS at `135.148.219.175` (`vps-8087ef2d`, Ubuntu 26.04, 2 vCPU, 3.7 GiB). **You have no SSH or server access and never need it.** The full plan is appended after `===PLAN===` (see `docs/BUILD-PLAN.md` on `main`). Read `CLAUDE.md`, `AGENTS.md`, `docs/STATUS.md`, `docs/frontend-inventory.md`, `docs/TESTING.md`, `docs/SECURITY.md` and `docs/DATABASE.md` first.

## You may edit ONLY these paths

- `app/**`, `migrations/**`, `tests/**`, `scripts/e2e_seed.py`, `app/pilot_seed.py`, `tests/route_inventory.txt`
- Excluded from `tests/**`: Lane 1 owns `tests/test_deploy*.py`, `tests/test_image_workflow.py`, `tests/test_ci_*.py` and `tests/test_db_roles.py`
- `web/src/components/tenant/**`, `web/src/lib/tenant*.ts`, `web/src/lib/audience*.ts` (the #45 web side)
- The #37 rebuild's files (branch `claude/project-thread-3nrr4u`): merge it **first**. After that, `web/package.json` and `web/wrangler.jsonc` belong to Lane 1.
- Docs: `docs/STATUS.md`, `docs/readiness/**`, `CLAUDE.md`, `AGENTS.md`, `docs/kb/**` except `kb/10` and `kb/13`, `docs/frontend-inventory.md`, `docs/multi-tenant-portals.md`, `docs/security/evidence/app-*.md`, `docs/evidence/**`

**Never edit:** `.github/**`, `deploy/**`, `Dockerfile`, `pyproject.toml`, `uv.lock` (request dependency changes from Lane 1 in `docs/STATUS.md` under "Requests to Lane 1"), `web/src/lib/api/**`, other `web/**`, `audit_engine/**` (parked until Stage 3; don't touch branch `claude/engine-core`), and `ai_adapter/**` (frozen, except a fix a security scan requires).

## Items, in order (the plan's Part 4.4 L2-x and 4.5)

1. **L2-0:** merge PR #90 (branch `claude/project-thread-mzpwa3`, adds a Postgres service to CI; its CI already passed). Update from `main` first if needed.
2. **L2-1: #37 rebuild.** Open a PR from `claude/project-thread-3nrr4u`. Tests, in `web/`: `npm run test:unit`, `npm run lint`, `npm run typecheck`, `npm run build:cloudflare:production` (must embed `https://api.kiensolutions.com`), `npm run test:e2e`. Merge, then close #37 with a link.
3. **L2-2: #40 rebuild.** Branch `claude/resend-report-ready` is 51 commits behind, so `git merge origin/main` first. Explain or revert its `migrations/env.py` change. Confirm password-reset email works on `main`. Tests: `uv run pytest -q tests/test_report_ready_email.py tests/test_password_reset.py tests/test_report_workflow.py`. Acceptance: a mail failure never fails sign-off, no findings or report content in the email, and no addresses logged. Close #40.
4. **L2-3: #45 rebuild.** Branch `claude/project-thread-498tby`: backend WIP with `app/tenancy.py`, `app/cors.py`, `app/api/tenant.py`, migrations `a118_firm_portal_slug` and `a119_firm_logo_url`, and `tests/test_portal_tenancy.py`.
   - Fix `docs/multi-tenant-portals.md`, which wrongly says `a111`/`a112`.
   - Check that the web tenant files match the backend.
   - Tests: `uv run pytest -q tests/test_portal_tenancy.py tests/test_route_isolation.py tests/test_origin_check.py tests/test_backend_api.py tests/test_deployment_migration.py`; in `web/`, `npm run test:unit && npm run test:e2e`.
   - Run a **separate independent security review pass**: cross-tenant denial on every new route; wrong-portal sign-in returns 403 and sets no cookie; no cookie `Domain`; exact CORS allowlist. Merge only on PASS. No Terraform or DNS. Close #45.
5. **L2-4: Doc corrections.**
   - `docs/STATUS.md`: AI is not "nothing built" (`ai_adapter/` skeleton is on `main`, off, empty allowlist). Add the single environment, the mock gap, and the G1/G2/G3 gates.
   - `CLAUDE.md` and `AGENTS.md`: single environment until pilot-ready (Abdullah, 2026-11-09); rule 7 (preview first) paused; engine frozen until Abdullah signs off the Stage 2 security audit; code agents never access servers.
   - Record the conflict between readiness item 41 and `CLAUDE.md` rule 10 in `docs/kb/19-open-questions.md`.
6. **L2-5: Security proof suite.** Put it in a new `tests/security/` folder, plus `docs/security/evidence/app-<id>.md` for each control (what it proves, the command, the result, the commit):

   | ID | Control | Proof |
   |---|---|---|
   | S-01 | Argon2id | The hash starts with `$argon2id$`; verify and rehash work |
   | S-02 | Cookie flags | `HttpOnly`, `Secure` in production, `SameSite=Lax`, no `Domain` |
   | S-03 | CSRF | Every state-changing route in `route_inventory.txt` rejects a foreign Origin |
   | S-04 | Auditor TOTP MFA | An auditor without MFA can't reach `/auditor/*`; recovery codes are single-use and hashed |
   | S-05 | Invite-only clients | No sign-up route; invites expire and are single-use |
   | S-06 | Session expiry and revocation | An expired token returns 401; a revoked `sid` returns 401; sign-out, reset and role change revoke sessions |
   | S-07 | Rate limiting and lockout | Existing tests |
   | S-08 | Tenant isolation | A **meta-test** fails if any route lacks a cross-tenant denial test |
   | S-09 | Clients never see findings | A meta-test: client routes never serialize finding fields |
   | S-10 | Upload scanning, quarantine, limits, and SAR items not uploadable | Tests |
   | S-11 | Secrets | Nothing secret in `NEXT_PUBLIC_*`; config only through `app/config.py`; `SecretStr` |
   | S-12 | Logs and Sentry | No document content, SAR terms, tokens or emails |
   | S-13 | Audit hash chain | Append-only |
   | S-14 | Authorization | Server-side for every role |
   | S-15 | Report rich-text sanitizer | No attributes, scripts or URLs |
   | S-19 | Downloads | Authorized on every request; presigned links short-lived |

7. **L2-6: Backend routes for every mocked contract.** Write them exactly to `web/src/lib/api/types.ts` and the table in `docs/frontend-inventory.md`, as small PRs in this order:
   - (a) firm team, branding (logo stored in R2), rubric (criteria stay empty for Quentin), request templates
   - (b) checklist tests and conclusions, engagement documents
   - (c) workpapers and review (reviewer must differ from preparer), samples
   - (d) findings CRUD and status, response-request release (approved findings only), client response requests and replies (**never join finding fields**)
   - (e) report draft, sections, `.docx` and PDF from `templates/report`, client reports (available only once signed)
   - (f) independence, sign-off (review, partner, complete; the server computes the fingerprint)
   - (g) activity, notifications, search (assigned engagements only)
   - (h) client invoices

   Every route must:
   - enforce `firm_id` and auditor assignment
   - have a **cross-tenant denial test**
   - write the audit chain for state changes
   - be added to `tests/route_inventory.txt`
   - be covered by `tests/test_client_view_allowlist.py` where clients can call it

   Add migrations as additive Alembic revisions, with an upgrade and downgrade test in a `*_postgres.py` test. If a contract has to change, update `docs/frontend-inventory.md` in the same PR and title it `CONTRACT-CHANGE: ...`. Tests per group: `uv run pytest -q tests/test_<group>.py tests/test_route_isolation.py tests/test_client_view_allowlist.py tests/test_responses_requested.py`.
8. **L2-7: Storage complete.**
   - Upload and download through R2 (S3 API), with authorization checked on every download and only short-lived presigned links.
   - ClamAV scan before a file becomes available; quarantine otherwise.
   - SHA-256 fingerprints.
   - A retention rule, plus export and deletion of one client firm's data on request (readiness item 25).
   - Tests: `tests/test_s3_storage.py`, `tests/test_upload_scanning.py`, `tests/test_document_ingestion.py`, new `tests/test_storage_retention.py`.
9. **L2-8: Flows complete.**
   - Email: invite, reset, magic link, report-ready.
   - Invoicing.
   - Client onboarding.
   - Checklist N/A: N/A sorts last, original numbers kept, undo restores the previous state.
   - Reports: edit, finalize with a hash, reopen.
   - Both portals and firm subdomains.
   - Tests: `uv run pytest -q tests/test_checklist_na.py tests/test_invoices.py tests/test_onboarding.py tests/test_report_workflow.py tests/test_password_reset.py`.
10. **L2-9:** `app/pilot_seed.py` (three synthetic firms with portal slugs, engagements, an auditor, and invitations sent through Resend; refuses `INVITATION_PREVIEW_ENABLED` in production; prints no tokens) and `scripts/e2e_seed.py` (everything Lane 1's e2e-live specs need). Both are idempotent and use synthetic names only. Add `tests/test_pilot_seed.py`.
11. **L2-10:** `docs/readiness/STATUS.md`: all 45 readiness items, each with a status, an evidence link and an owner. Mark an item Done only with evidence.

## Loop for every item

1. Create `lane2/<item>` from `origin/main`, or reuse the named existing branch. Catch up with `git merge origin/main` (a real merge commit).
2. Make the smallest change.
3. Run the item's tests, then the full gate:
   - `uv sync --frozen && uv run ruff check . && uv run pytest -q`
   - for web-touching PRs: `cd web && npm ci && npm run lint && npm run typecheck && npm run test:unit && NEXT_PUBLIC_USE_MOCKS=true npm run build:cloudflare && npx playwright install --with-deps chromium && npm run test:e2e && npm run test:e2e:live`
   - the Security workflow, once it exists
4. If something fails, fix it. At most **3 attempts** on the same failure.
5. Open a PR listing the exact commands and their results.
6. **Independent verify:** a separate review pass or subagent re-runs the tests and checks the acceptance criteria and hard limits. At most **2 rounds**.
7. **You merge your own PRs on green** (CI, Security and verify PASS) with a **merge commit**. Never rebase, squash or force-push. Do not ask Slave Kien or a Cursor agent to merge for you.
8. Add one line to `docs/STATUS.md`.
9. **When blocked:** choose the safest option, write `DECISION:` or `BLOCKED(owner): <input>` in `docs/STATUS.md`, and move on.

If Postgres can't run in your sandbox (for example, initdb refusing root), say so and rely on CI's Postgres job. **Never claim an unrun test passed.** Commit as `abdullah-kynetic <211030198+abdullah-kynetic@users.noreply.github.com>`.

## Hard limits

- Never touch the old shared server **40.160.150.91**. You have no server access.
- No SAR material to any model. Items AML-BD-017 and AML-BD-025 are restricted: metadata only, human-only.
- Synthetic data only.
- No secrets anywhere. Variable names only; never read `.env`.
- No model calls, and no `audit_engine` work.
- No Google Drive.
- Neutral black-and-white design.
- Clients never see findings, only released "Responses requested".
- Only an auditor action approves findings or signs reports.
- Spell it "Quentin". Leave rubric criteria empty.
- Keep `tests/test_workflow_boundary.py` passing.

## Report at the end (and at each hourly checkpoint)

- PRs merged (links), the open PR, the exact commands and results
- security proof table status
- route groups done and remaining
- the `BLOCKED(owner)` list
- requests for Lane 1
