# Kien build plan v2: staged (Foundation, then Security audit, then AML engine)

Revised 2026-11-09, 3:25 PM PST (Codex lanes + new VPS details). Supersedes [PLAN.md](PLAN.md) (v1, kept for reference) on **sequencing and scope**. Repo facts were read read-only from GitHub at `main` = `9043e24` (merge of #89). Public URLs were fetched the same day. **[unverified]** marks anything not checked.

---

## Part 1: Plain English (for Abdullah)

There are three stages, each with a gate.

1. **Stage 1, Foundation (fully automated).** The whole product has to be finished, working and secure before any real document goes in. That means:
   - every page and button wired to the real backend, with no mock or demo data in the production build
   - file storage, virus scanning, encryption and retention working, plus email, invoicing, client onboarding, the checklist (including N/A ordering), reports, both portals and firm subdomains
   - every security and sign-in control proven by a test or command, with an evidence file
   - the new server set up, locked down and backed up

   Slave Kien runs the server. Two **OpenAI Codex cloud** coding agents (Code Lane 1 and Code Lane 2) split the code work by folder, so they never edit the same files. Each lane merges its own PRs on green with merge commits. Codex has no SSH or VPS access.
   **Gate:** Slave Kien runs the "Stage 1 done" checklist (Part 6) and reports it green.
2. **Stage 2, Security-skill audit in Claude Code.** We install free, open-source security review skills (all checked to exist, see Part 7) and run them against the repo and the live site. Claude fixes what they find and re-runs until clean.
   **Gate:** you check the results and say "Stage 2 signed off".
3. **Stage 3, the AML engine, in Claude.** It starts **only after** your Stage 2 sign-off. Until then the `claude/engine-core` branch stays parked: no engine work, no engine PRs.

**Honest time** (details in Part 9). The five-hour window is enough for:
- all of Phase 1
- security scanning in CI
- the deploy code
- the server going up
- the full page-and-button inventory

Finishing every screen on the real backend is the big piece. About 40 front-end functions still run on fake browser data, including in the production build today. That's **several days** of agent work (about 3–6), not hours. Stage 2 is about a day once Stage 1 is green. Stage 3 is weeks of iteration.

**What I need from you** (Part 8): the server login, plus keys for R2 storage, Resend email, Cloudflare, and later OpenRouter (Stage 3 only). Also a yes to moving `api.kiensolutions.com` to the new server.

---

## Part 2: Facts (carried over from v1, plus new findings)

### 2.1 Environments: collapse to one

Unchanged from v1 Part 2(a):
- **Use one web Worker,** `ains-platform` (`web/wrangler.jsonc` `env.production`), on `auditor.kiensolutions.com` plus one host per synthetic pilot firm.
- **Use one API,** `api.kiensolutions.com`, on the new VPS. Today it resolves to **40.160.150.91, the old shared server: never touch it**.
- **Freeze:** `ains-platform-demo`, `kien-signin-preview` (preview.kiensolutions.com), `kien-shadcn-preview` (layout.kiensolutions.com) and `kien-demo-live`, plus `web/wrangler.preview.jsonc` and `web/wrangler.layout.jsonc`. They're all live today. Don't delete them.
- **Remove:** `STAGING_HOST` from `deploy/Caddyfile` and `deploy/.env.example`.

### 2.2 Phase 1 leftovers (unchanged from v1 Part 2(b), all agent work)

- **#90 (PostgreSQL tests in CI):** green on CI run 42711698018. Merge.
- **Image workflow:** failed on `9043e24` (run 42711094683, at the build-push step; cause **[unverified]**). Fix it.
- **#37 rebuild** (`claude/project-thread-3nrr4u`): done. No PR yet.
- **#40 rebuild** (`claude/resend-report-ready`): done, but 51 commits behind main. Merge `main` in.
- **#45 rebuild** (`claude/project-thread-498tby`): backend WIP only. The doc names the migrations wrong; the files are `a118`/`a119`. It still needs the web check and a security review.
- **Doc corrections:**
  - `docs/STATUS.md` says "AI: nothing is built yet", but `ai_adapter/` is on `main`.
  - Readiness item 41 conflicts with `CLAUDE.md` rule 10 on OpenRouter.
  - `Dockerfile` doesn't copy `ai_adapter/` (and `audit_engine/` once Stage 3 lands).
  - The memory limits in `deploy/docker-compose.prod.yml` add up to 4.4 GB, more than the new VPS (3.7 GiB). Tune them down in L1-3.
- **Engine branch** `claude/engine-core`: **parked until Stage 3** (it has one known test false match and two failures nobody has looked at).

### 2.3 New: production still contains mock data (the full-product gap)

- `docs/frontend-inventory.md` lists the screen contracts still on a typed mock layer (`web/src/lib/mock/*`, persisted in `localStorage` `kien-mock-*`).
- `web/src/lib/api/*` has **41 `TODO(backend)` markers** across 13 files: `checklist.ts` 2, `documents.ts` 1, `findings.ts` 4, `firm.ts` 7, `log.ts` 2, `notifications.ts` 3, `portal.ts` 5, `report.ts` 3, `samples.ts` 3, `search.ts` 1, `signoff.ts` 6, `types.ts` 1, `workpapers.ts` 3.
- At least `web/src/lib/api/firm.ts` (team, branding, rubric, templates) reads and writes `localStorage` **with no `USE_MOCKS` check**, so the production build ships mock behaviour there.
- Mocked contracts still needing real backend routes (from `docs/frontend-inventory.md`):
  - checklist tests and conclusions
  - engagement documents
  - workpapers and review
  - samples
  - findings (CRUD and status)
  - report draft, sections and `.docx`
  - independence
  - sign-off (review, partner, complete)
  - activity
  - firm team, branding (logo to object storage), rubric and request templates
  - notifications
  - search
  - response-request release, client response requests and replies
  - client reports
  - client invoices
- Already real (per the inventory doc): clients, contacts, engagement summaries, invoicing, report writing (`/auditor/reports`), pipeline, tasks, questionnaire, uploads, onboarding.
- Real-API browser tests exist only for sign-in: `web/e2e-live/sign-in-live.spec.ts`, using `web/playwright.live.config.ts` and `scripts/e2e_backend.py` (the real local backend with synthetic users). All other e2e specs in `web/e2e/` run against mocks (`NEXT_PUBLIC_USE_MOCKS=true`).
- `tests/route_inventory.txt` (71 lines) is the backend route list, guarded by tests.

### 2.4 Security facts seen in code (spot checks; Stage 1 must prove each with a test)

- Argon2 via `pwdlib[argon2]` (`pyproject.toml`).
- Signed session tokens with `exp` (`app/auth/security.py`; `session_ttl_hours=12` in `app/config.py`). An `AuthSession` table with `revoked_at` exists (`app/database/models.py`).
- Origin allowlist on state-changing requests (CSRF control, `app/origin_check.py`); CORS from `CORS_ORIGINS` (`app/main.py`); rate limiting and lockout (`app/ratelimit.py`, `app/auth/lockout.py`).
- Web security headers in `web/next.config.ts`: HSTS and `X-Frame-Options DENY` were seen. **No Content-Security-Policy was found [verify]**. Caddy sets HSTS, nosniff and Referrer-Policy (`deploy/Caddyfile`).
- **Least-privilege database roles: not present.** Compose uses one `POSTGRES_USER` for both migrations and the app.
- CodeQL code scanning is **not free for private repositories**. It needs GitHub Code Security ($30 per active committer per month, per docs.github.com). The repo is private. **Use Semgrep CE and Bandit instead.**

---

## Part 3: Stage gates

| Gate | Passes when | Who checks |
|---|---|---|
| **G1: Stage 1 done** | Every row in Part 6 is green, with an evidence file in the repo | Slave Kien runs Part 6 and reports to Abdullah |
| **G2: Stage 2 signed off** | Every Stage 2 skill was run, findings were fixed or accepted in writing, the final re-run is clean (no open High or Critical), and Abdullah says "Stage 2 signed off" | Abdullah |
| **G3: Stage 3 start** | G2 is passed. No engine branch work, PR or merge happens before this | Slave Kien refuses to launch engine work before G2 |

---

## Part 4: Stage 1, Foundation (automated)

### 4.1 Lanes and file ownership

**Where the lanes run (2026-11-09):** Code Lane 1 and Code Lane 2 both run in **OpenAI Codex cloud** (not a Cursor agent and not Claude for Stage 1 code). Each lane opens PRs, waits for green CI, and merges its own PRs with **merge commits** only. **Lane C (Slave Kien)** does all VPS work over SSH. Codex has **no SSH access** and never needs it.

| Path | **Code Lane 1** (CI, deploy, web wiring) | **Code Lane 2** (backend, auth and security, rebuilds) | **Lane C** (Slave Kien, VPS) |
|---|---|---|---|
| `.github/**`, `Dockerfile`, `.dockerignore`, `docker-compose.yml`, `deploy/**` | **owns** | read | applies on the VPS; never edits the repo |
| `docs/runbooks/**`, `docs/security/**` (scan reports, evidence index), `scripts/security/**` | **owns** | writes evidence files only under `docs/security/evidence/app-*` | provides VPS evidence text |
| `tests/test_deploy*.py`, `tests/test_image_workflow.py`, `tests/test_ci_*.py` | **owns** | read | — |
| `pyproject.toml`, `uv.lock`, `web/package.json`, `web/package-lock.json` | **owns** after B-37 merges (audit bumps) | lands #37's `web/package.json` change first, then requests changes in `docs/STATUS.md` | — |
| `web/next.config.ts` (headers and CSP), `web/scripts/build-guard.mjs`, `web/wrangler.jsonc` (after #37) | **owns** | read | runs `wrangler deploy` |
| `web/src/lib/api/**`, `web/src/lib/*-api.ts`, `web/src/lib/api.ts`, `web/src/lib/mock/**`, `web/src/app/**`, `web/src/components/**` **except** `components/tenant/**` | **owns** (replaces mocks with real calls and fixes UI states) | read | — |
| `web/e2e/**`, `web/e2e-live/**`, `web/playwright*.ts`, `scripts/e2e_backend.py` | **owns** | may add backend seed hooks only through `scripts/e2e_seed.py` (Lane 2 owns it) | — |
| `docs/inventory/PRODUCT-INVENTORY.md` | **owns** | read; updates the "backend" column through its PRs' descriptions | — |
| `app/**`, `migrations/**`, `tests/**` (all others), `tests/route_inventory.txt`, `scripts/e2e_seed.py`, `app/pilot_seed.py` | read | **owns** | — |
| `web/src/components/tenant/**`, `web/src/lib/tenant*.ts`, `web/src/lib/audience*.ts` (#45 web side) | read | **owns** | — |
| `docs/STATUS.md`, `docs/BUILD-PLAN.md`, `docs/readiness/**`, `CLAUDE.md`, `AGENTS.md`, `docs/kb/**`, `docs/frontend-inventory.md`, `docs/multi-tenant-portals.md` | `BUILD-PLAN.md` (first PR) and `docs/kb/10`, `docs/kb/13` | **owns the rest** | — |
| `audit_engine/**`, `ai_adapter/**` | **frozen until G3** | **frozen until G3** (a bug fix to `ai_adapter` only if a security scan requires it) | — |
| The VPS | never | never | **owns** |
| Old server 40.160.150.91 | never | never | never (refuse if the target matches) |

**Contract between Lane 1 and Lane 2:**
- The API shapes are the ones in `web/src/lib/api/types.ts` and the route table in `docs/frontend-inventory.md`.
- Lane 2 implements those routes exactly. If a shape must change, Lane 2 changes `docs/frontend-inventory.md` in the same PR and adds `CONTRACT-CHANGE:` to the PR title.
- Lane 1 swaps each mock function body for a real `fetch` once the matching Lane 2 route is merged.
- Until a route exists, the production build must fail loudly with a visible "Not available yet" state. It must not fall back to `localStorage`.

### 4.2 Git and merge rules (both code lanes)

- Each lane merges **its own** PRs. Before merging, update the branch with `git merge origin/main` (real merge commit). **Never rebase, squash or force-push.** Merge with a **merge commit** only.
- **Merge on green:** both CI jobs pass, plus the new `Security` workflow, plus an independent verify PASS.
- Keep PRs small: one route group or one concern each, under about 600 changed lines (#45 is the exception).
- Commit identity: `abdullah-kynetic <211030198+abdullah-kynetic@users.noreply.github.com>`.
- If the other lane merged into a file you need, merge `origin/main` again. Never edit the other lane's files. Request the change in `docs/STATUS.md` under "Requests to Lane N".

### 4.3 The loop (every item)

```
1. Branch from origin/main (lane1/<item> or lane2/<item>), or reuse the named existing branch and git merge origin/main.
2. Build the smallest change that meets the acceptance criteria.
3. Run the item's tests, then the full gate:
     uv sync --frozen && uv run ruff check . && uv run pytest -q
     cd web && npm ci && npm run lint && npm run typecheck && npm run test:unit \
       && NEXT_PUBLIC_USE_MOCKS=true npm run build:cloudflare && npm run build:cloudflare:production \
       && npx playwright install --with-deps chromium && npm run test:e2e && npm run test:e2e:live
     (security gate, once S-CI exists) the commands in 4.5 row S-CI
4. Fails? Fix and re-run. At most 3 attempts on the same failure.
5. Push and open a PR. The body lists the exact commands run and their pass/fail counts, plus links to new evidence files.
6. Independent verify. A separate agent or session that did not write the change reads the diff and the acceptance
   criteria, re-runs the item's tests, and checks the hard limits (Part 5). It answers PASS or a list of defects.
   At most 2 rounds.
7. Merge on green CI plus verify PASS (merge commit). Add one line to docs/STATUS.md
   (Lane 2) or to the PR plus BUILD-PLAN checkbox (Lane 1).
8. Blocked (3 failed attempts, 2 failed verify rounds, a missing owner input, or an unclear spec): pick the safest option,
   record "DECISION:" or "BLOCKED(owner): <input>" in docs/STATUS.md, and move to the next item. Never stop the whole run.
   Never ask Abdullah routine questions.
```

If PostgreSQL can't run in an agent sandbox, say so and rely on CI's Postgres job (after #90). Never claim an unrun test passed.

### 4.4 Work items

#### Code Lane 1: CI security scanning, image fix, deploy code, runbooks, web wiring

| ID | Item | Acceptance | Tests / commands |
|---|---|---|---|
| L1-0 | Commit this plan as `docs/BUILD-PLAN.md` (first PR) | File on `main` | CI green |
| L1-1 | Image workflow fix | `image.yml` succeeds on `main`; the digest is recorded in `deploy/RELEASES.md` with "Deployed to: none" | `gh workflow run image.yml --ref main`; read the failing log and fix; `uv run pytest -q tests/test_image_workflow.py` |
| L1-2 | **S-CI security workflow** `.github/workflows/security.yml`, run on PRs and `main`, all tools free (see 4.5) | Every scanner runs and fails the job on High or Critical (or on any verified secret). An allowlist file `docs/security/accepted-risks.md` (each entry has a reason and an expiry date) is the only way to suppress a finding. Reports upload as artifacts | The commands in 4.5 row S-CI |
| L1-3 | Single-environment deploy code (v1 item B5, unchanged in scope; see `PLAN.md` 3.7 B5) | Covers: Caddyfile without `STAGING_HOST`; compose tuned to fit 3.7 GiB with ClamAV `ConcurrentDatabaseReload=no`; the `ai-adapter` service **defined but `AI_ENABLED=false`**; Dockerfile copies `ai_adapter`; `deploy/deploy.sh`, `rollback.sh` and `build-on-host.sh`; `deploy/bootstrap/harden.sh` (refuses 40.160.150.91) and `install-timers.sh`; `docs/runbooks/vps-bringup.md`; updates to `docs/kb/10` and `docs/kb/13`. **Add least-privilege DB roles:** a `kien_migrator` owner role used only by `migrate`, a `kien_app` role (DML only, no DDL) used by the api and worker, and a `kien_backup` read-only role used by `backup.sh`, all created by `deploy/bootstrap/db-roles.sql`. Add Caddy CSP and Permissions-Policy headers for the API | `uv run pytest -q tests/test_deploy_prod.py tests/test_deploy_scripts.py tests/test_deploy_single_env.py`; `shellcheck deploy/*.sh deploy/*/*.sh`; `docker compose ... config -q`; `caddy validate` (exact forms in `PLAN.md` 3.7 B5); new `tests/test_db_roles.py` (Postgres: `kien_app` can't `CREATE TABLE` or `DROP`, and can SELECT, INSERT, UPDATE and DELETE app tables; audit-log table is append-only for `kien_app` if feasible) |
| L1-4 | Web security headers | `web/next.config.ts` sends a strict **Content-Security-Policy** (no `unsafe-eval`; `connect-src` limited to the API origin and Sentry if used), HSTS, `X-Content-Type-Options`, `Referrer-Policy`, `Permissions-Policy` and `frame-ancestors 'none'` | New `web/e2e-live/headers-live.spec.ts` asserts the headers on the production build; `npm run build:cloudflare:production` |
| L1-5 | **Product inventory** `docs/inventory/PRODUCT-INVENTORY.md` (see 4.6) | Every page in `web/src/app/**/page.tsx`, every button or action in its components, the API function it calls, the backend route (from `tests/route_inventory.txt` and `app/api/*` decorators), the status (built / mocked / missing), the Lane 2 item that will build it, and the e2e-live spec that proves it. Also every backend route that no UI uses | New `scripts/security/inventory_check.mjs` (or `.py`) fails CI if any `TODO(backend)` remains in `web/src/lib/**`, or if a page has no row. It's allowed to fail until the end of Stage 1; it becomes blocking at G1 |
| L1-6 | **No mocks in production builds** | `web/scripts/build-guard.mjs` fails `build:cloudflare:production` if the bundle contains `kien-mock-` keys, `web/src/lib/mock` imports or seed data. Every `web/src/lib/api/*` function calls the real API when `USE_MOCKS` is false (no `localStorage` fallback) | `node --test web/scripts/build-guard.test.mjs` (extended); `npm run build:cloudflare:production && npm run guard:build` |
| L1-7 | **Wire every mocked function** to Lane 2's routes as they merge (team, branding, rubric, templates, checklist tests, documents, workpapers, samples, findings, report draft and docx, independence, sign-off, activity, notifications, search, response requests, client reports, client invoices) | Each function has a real body, error and loading states, and **one e2e-live spec per flow** against the real backend (`scripts/e2e_backend.py`), covering both roles and a denial case | `npm run test:e2e:live`; specs `web/e2e-live/<flow>-live.spec.ts`, listed in 4.6 |
| L1-8 | Wrangler production routes | `env.production` custom domains: `auditor.kiensolutions.com` and the synthetic pilot firm hosts; `vars.NEXT_PUBLIC_AUDITOR_HOST` | `npm run build:cloudflare:production` |
| L1-9 | Runbooks | `docs/runbooks/{vps-bringup,deploy,rollback,restore,incident,secrets-rotation}.md`, each with exact commands and verification steps | Docs. The verifier checks every command against the real script names |

#### Code Lane 2: app-level auth and security hardening, tests, #37/#40/#45 rebuilds, missing backend routes

| ID | Item | Acceptance | Tests / commands |
|---|---|---|---|
| L2-0 | Merge #90 | CI on `main` shows "Postgres tests must run, not skip" passing | CI |
| L2-1 | #37 rebuild (`claude/project-thread-3nrr4u`). **Merge first**; Lane 1 owns `web/package.json` and `wrangler.jsonc` after this | Production build embeds `https://api.kiensolutions.com`; close #37 | In `web/`: `npm run test:unit` (includes `scripts/wrangler-public-api-url.test.mjs`), `npm run build:cloudflare:production` |
| L2-2 | #40 rebuild (`claude/resend-report-ready`, merge `main` in) | A mail failure never fails sign-off; no findings or report content in the email; no addresses logged; reset email confirmed on `main`; close #40 | `uv run pytest -q tests/test_report_ready_email.py tests/test_password_reset.py tests/test_report_workflow.py` |
| L2-3 | #45 rebuild (`claude/project-thread-498tby`) with an **independent security review** | Doc migration names fixed; host-to-firm binding; wrong-portal sign-in returns 403 with no cookie; no cookie `Domain`; CORS allowlist; web tenant files match; close #45 | `uv run pytest -q tests/test_portal_tenancy.py tests/test_route_isolation.py tests/test_origin_check.py tests/test_backend_api.py tests/test_deployment_migration.py`; `npm run test:unit`; `npm run test:e2e` (tenant-host, tenant-api) |
| L2-4 | Doc corrections | `STATUS.md` (AI adapter exists, single environment, mock gap, G1/G2/G3 gates); `CLAUDE.md` and `AGENTS.md` note: single environment, rule 7 paused, engine frozen until G2; readiness item 41 conflict recorded in `docs/kb/19-open-questions.md` | CI |
| L2-5 | **Security proof suite** (rows S-01 to S-20 in 4.5): one test module per control, plus an evidence file `docs/security/evidence/app-<id>.md` (what it proves, the command, the result, the commit) | Every row has a passing test | `uv run pytest -q tests/security/` (new folder) |
| L2-6 | **Backend routes for every mocked contract**, in small PRs in this order: (a) firm team, branding (logo to R2), rubric, templates; (b) checklist tests and conclusions, documents; (c) workpapers and review, samples; (d) findings, response-request release, client response requests and replies; (e) report draft, sections, `.docx` and PDF, client reports; (f) independence, sign-off (review, partner, complete); (g) activity, notifications, search; (h) client invoices | Each route enforces `firm_id` and auditor assignment; has **a cross-tenant denial test**; writes the audit chain for state changes; matches `types.ts` exactly; is added to `tests/route_inventory.txt`; and clients get only allowlisted fields (`tests/test_client_view_allowlist.py` extended). Response requests never join finding fields | `uv run pytest -q tests/test_<group>.py tests/test_route_isolation.py tests/test_client_view_allowlist.py tests/test_responses_requested.py`; Postgres migration tests through CI |
| L2-7 | **Storage complete** | Upload to R2 via the S3 API, with a short-lived download presign or a streamed download that checks authorization on every request; ClamAV scan before the file is stored as available (quarantine otherwise); server-side encryption at rest (R2 encrypts by default, which Lane C verifies); a documented retention rule plus deletion and export of one client's data on request (readiness item 25); SHA-256 fingerprints | `uv run pytest -q tests/test_s3_storage.py tests/test_upload_scanning.py tests/test_document_ingestion.py tests/test_storage_retention.py` (new); live check by Lane C (C5) |
| L2-8 | **Flows complete end to end:** email (invite, reset, magic link, report-ready); invoicing; client onboarding (invite, accept, set password, walkthrough); checklist including **N/A ordering** (N/A sorts last, original numbers kept, undo restores the previous state); reports (edit, finalize with a hash, reopen); both portals; firm subdomains | Backend tests exist and pass; Lane 1's e2e-live spec per flow passes | `uv run pytest -q tests/test_checklist_na.py tests/test_invoices.py tests/test_onboarding.py tests/test_report_workflow.py tests/test_password_reset.py` |
| L2-9 | `app/pilot_seed.py` and `scripts/e2e_seed.py` | Idempotent, synthetic names only; refuses invitation previews in production; seeds everything the e2e-live specs need | `uv run pytest -q tests/test_pilot_seed.py` |
| L2-10 | Readiness tracker `docs/readiness/STATUS.md` (all 45 items: status, evidence link, owner) | Done only with evidence | CI |

#### Lane C: Slave Kien on the VPS

**New VPS (owner-provided 2026-11-09):** `135.148.219.175` (hostname `vps-8087ef2d`), Ubuntu 26.04, 2 vCPU, 3.7 GiB RAM. Slave Kien handles **all** VPS work over SSH. Codex has no SSH access. Never touch the old shared server `40.160.150.91`.

Same steps as v1 `PLAN.md` 3.7 Lane C, C0–C9. **C10 (AI eval) moves to Stage 3.** Additions:
- **C1+:** add the evidence for S-21 (firewall) and S-22 (SSH hardening), as in 4.5.
- **C4+:** create the DB roles from `deploy/bootstrap/db-roles.sql`, and prove the app role can't run DDL.
- **C5+:** verify R2 encryption at rest and bucket privacy:
  - no public access
  - anonymous GET returns 403
  - object lock or retention set on the backup bucket
- **C6+:** restore drill into a scratch container, plus a fresh-box restore of a synthetic engagement (readiness item 33).
- **C9+:** run the Lane 1 e2e-live suite against the live hosts:

  ```
  PLAYWRIGHT_BASE_URL=https://auditor.kiensolutions.com npm run test:e2e:live
  ```

  plus the per-firm hosts. Then run the external checks in 4.5 rows S-17 and S-21: `testssl.sh` or `curl -I` for headers and TLS, and `nmap -Pn -p- <VPS_IP>` showing only 22, 80 and 443.
- **C11:** hand all evidence text to Lane 2 for `docs/security/evidence/vps-*.md` and `docs/evidence/vps/`.

### 4.5 Security and authentication controls: each needs a test or command plus an evidence file

Evidence file names: `docs/security/evidence/<id>.md` (one file per row). Each holds the control, the command, the output summary, the date and the commit SHA. No secrets.

| ID | Control | Proof (test or command) | Lane |
|---|---|---|---|
| S-01 | Passwords hashed with Argon2id, never stored plain | `tests/security/test_password_hashing.py`: the stored hash starts with `$argon2id$`; verify and rehash work; plain text not found in the DB | 2 |
| S-02 | Session cookie `HttpOnly`, `Secure` in production, `SameSite=Lax`, no `Domain` | `tests/security/test_cookies.py` (production settings) | 2 |
| S-03 | CSRF: cross-site POST, PUT, PATCH and DELETE rejected (exact-origin allowlist) | `tests/test_origin_check.py`, plus `tests/security/test_csrf.py` covering every state-changing route in `route_inventory.txt` | 2 |
| S-04 | TOTP MFA required for auditors; recovery codes single-use and hashed | `tests/security/test_auditor_mfa.py` (an auditor without MFA can't reach `/auditor/*`) | 2 |
| S-05 | Clients are invite-only (no self sign-up); invitations expire and are single-use | `tests/security/test_invite_only.py`; `tests/test_auth_readiness.py` | 2 |
| S-06 | Session expiry (12 h) and revocation (sign-out, password reset and role change revoke sessions) | `tests/security/test_sessions.py`: an expired token returns 401; a revoked `sid` returns 401; a reset revokes all of that user's sessions | 2 |
| S-07 | Rate limiting and account lockout | `tests/test_rate_limit.py`, `tests/test_signin_lockout.py`, `tests/test_signin_lockout_postgres.py`; live brute-force check by Lane C (C9) | 2, C |
| S-08 | Tenant isolation across firm subdomains and API paths | `tests/test_route_isolation.py`, `tests/test_portal_tenancy.py`; every route has a cross-tenant denial test; a meta-test fails if any route in `route_inventory.txt` lacks one | 2 |
| S-09 | Clients never see findings, only released "Responses requested" | `tests/test_client_view_allowlist.py`, `tests/test_responses_requested.py`, plus a meta-test that client routes never serialize finding fields; e2e-live `client-cannot-see-findings-live.spec.ts` | 2, 1 |
| S-10 | Upload scanning (ClamAV) and quarantine; type, size and zero-byte limits; restricted (SAR) items can't be uploaded | `tests/test_upload_scanning.py`, `tests/test_document_ingestion.py`; live EICAR test by Lane C | 2, C |
| S-11 | Secret handling: config only through `app/config.py`; `SecretStr`; nothing secret in `NEXT_PUBLIC_*`; no secrets in git | `tests/security/test_no_secrets_in_public_env.py`; the gitleaks and trufflehog steps (S-CI) | 2, 1 |
| S-12 | Logs and Sentry hold no document content, SAR terms, tokens or email addresses | `tests/test_monitoring.py`, plus `tests/security/test_log_scrubbing.py` | 2 |
| S-13 | Audit log is append-only with a hash chain | `tests/test_audit_log.py`, `tests/test_audit_postgres.py` | 2 |
| S-14 | Authorization is server-side for every role (UI gates aren't trusted) | `tests/test_auditor_assignment.py`, `tests/test_route_isolation.py` | 2 |
| S-15 | Input validation and output encoding (rich-text report sanitizer: no attributes, scripts or URLs) | `tests/security/test_report_sanitizer.py` | 2 |
| S-16 | Least-privilege database roles | `tests/test_db_roles.py` (L1-3); live proof by Lane C | 1, C |
| S-17 | Headers: CSP, HSTS, nosniff, Referrer-Policy, Permissions-Policy, frame-ancestors (web and API) | `web/e2e-live/headers-live.spec.ts`; live `curl -sI` on each host by Lane C | 1, C |
| S-18 | Backups encrypted, off-box, object-locked; restore proven | `deploy/backup/restore-drill.sh` and `lock-drill.sh` on the VPS with real R2 | C |
| S-19 | Storage authorization: a download needs a session plus firm/assignment authorization; presigned links are short-lived; no public bucket | `tests/test_s3_storage.py` (extended); live anonymous GET returns 403 | 2, C |
| S-20 | Dependency pinning and lockfiles enforced (`uv sync --frozen`, `npm ci`) | CI config check, `tests/test_ci_lockfiles.py` | 1 |
| S-21 | Firewall: only 22, 80 and 443 | `ufw status verbose`; external `nmap -Pn -p- <VPS_IP>` from the box | C |
| S-22 | SSH hardening: keys only, no root login, fail2ban | `sshd -T`; `fail2ban-client status sshd`; a password login attempt is refused | C |
| S-23 | Host patching | `unattended-upgrades --dry-run`; `apt list --upgradable` is empty after bootstrap | C |
| S-24 | Container hardening (read-only, `cap_drop ALL`, `no-new-privileges`, only Caddy publishes ports) | `tests/test_deploy_prod.py`; `docker inspect` on the VPS | 1, C |
| **S-CI** | **Dependency, secret, container and static scanning in CI** (`.github/workflows/security.yml`) | **pip-audit:** `uv export --frozen --no-dev --format requirements-txt > /tmp/req.txt && uvx pip-audit -r /tmp/req.txt --strict`. **npm audit:** `cd web && npm audit --omit=dev --audit-level=high`. **gitleaks** (MIT; run the binary, not the action): `gitleaks git --redact --exit-code 1 .`. **trufflehog** (AGPL-3.0, used as a tool only): `trufflehog git file://. --only-verified --fail`. **Trivy:** `trivy fs --scanners vuln,secret,misconfig --severity HIGH,CRITICAL --exit-code 1 .` and `trivy image --severity HIGH,CRITICAL --exit-code 1 kien-api:ci` (image built in the job). **Semgrep CE:** `semgrep scan --config p/python --config p/typescript --config p/owasp-top-ten --config p/secrets --error`. **Bandit:** `bandit -r app ai_adapter -ll -ii`. **zizmor** (MIT, GitHub Actions audit): `uvx zizmor .github/workflows`. **CodeQL:** skipped, since it isn't free on private repos (recorded in `docs/security/accepted-risks.md`) | 1 |

### 4.6 Product inventory (L1-5) format and the e2e-live spec list

`docs/inventory/PRODUCT-INVENTORY.md` columns: `Page route | UI action (button/form) | Component file | API client function | Backend route | Status (built / mocked / missing) | Backend item (L2-6x) | e2e-live spec | Roles tested | Denial tested`.

It must cover every `web/src/app/**/page.tsx`, including:
- auditor pages: Today, clients, engagements, plus the engagement tabs requests, documents, checklist, workpapers, samples, findings, report, independence, sign-off and activity
- pipeline, reports and print, invoices (new/edit/view), audit-log, workspaces/new
- firm team, branding, rubric and templates
- notifications, settings, the Cmd-K search
- client pages: home, upload, checklist, questionnaire, messages, progress, responses, report, invoices
- auth pages: sign-in, accept-invitation, account-setup, reset-password, the first-sign-in walkthrough

It also covers every route in `tests/route_inventory.txt`.

Required e2e-live specs, all run against the real backend via `scripts/e2e_backend.py` and `scripts/e2e_seed.py`, with no mocks:
- `sign-in-live` (exists)
- `mfa-live`, `invite-accept-live`, `password-reset-live`, `onboarding-live`
- `client-upload-live` (with scan states), `checklist-na-order-live`, `questionnaire-live`
- `auditor-review-documents-live`, `checklist-conclusions-live`, `workpapers-live`, `samples-live`
- `findings-and-release-live`, `client-responses-live`, `client-cannot-see-findings-live`
- `report-edit-finalize-live`, `report-docx-download-live`, `client-report-live`
- `independence-signoff-live`
- `invoices-live`, `client-invoices-live`
- `firm-team-live`, `firm-branding-logo-live`, `rubric-templates-live`
- `notifications-live`, `search-live`, `activity-live`
- `tenant-host-live` (firm A user refused on firm B host)
- `headers-live`

---

## Part 5: Hard limits (every lane, every stage; the verifier checks these)

1. **Never touch the old shared server 40.160.150.91.** No SSH, no deploys, no DNS pointing new hosts at it.
2. **No SAR material to any model, ever** (AML-BD-017 and AML-BD-025, or anything SAR-tagged, are blocked in code). No SAR content in logs, tests or prompts.
3. **No real client data** until all 45 readiness items are complete **and** G1 and G2 have passed **and** Abdullah says so in writing. Synthetic only.
4. **No secrets in the repo, PRs, logs, screenshots or chat.** Variable names only. Values go into `/etc/kien/*.env` (mode 600) through the secure form. Never print `.env`.
5. **Free models only, no paid fallback, and the ~$18 OpenRouter balance stays untouched.** No model work at all before G3.
6. **No Google Drive.**
7. **Neutral black-and-white design** (`DESIGN.md`, `CLAUDE.md` rule 8).
8. **Clients never see findings,** only auditor-released "Responses requested".
9. **Humans approve findings and sign reports.**
10. Spell it **Quentin**. Leave rubric criteria empty for Quentin.
11. Git: merge commits only. No rebase, squash or force-push. Never claim a test passed unless it ran.
12. Code lanes have **no VPS access**. Only Slave Kien operates servers.
13. **No engine work before G3.** `claude/engine-core` stays parked. `audit_engine/**` and `ai_adapter/**` are frozen except for a fix a security scan requires.
14. **No mock data in production builds** (enforced by L1-6).

---

## Part 6: "Stage 1 done" acceptance checklist (Slave Kien verifies; every row needs evidence)

**Phase 1 and repo**
- [ ] #90 merged; CI on `main` runs the Postgres tests with no skips
- [ ] The Image workflow on `main` is green; digest in `deploy/RELEASES.md`
- [ ] #37, #40 and #45 rebuilds merged; PRs #37, #40 and #45 closed with links; #45's security review PASS is attached
- [ ] Doc corrections merged (`STATUS.md`, `CLAUDE.md`, `AGENTS.md`, `kb/19`, the multi-tenant doc); `docs/BUILD-PLAN.md` on `main`
- [ ] `security.yml` green on `main`: pip-audit, npm audit, gitleaks, trufflehog, Trivy fs and image, Semgrep, Bandit, zizmor; `accepted-risks.md` has a reason and expiry for every exception

**Full product (no mocks)**
- [ ] `docs/inventory/PRODUCT-INVENTORY.md` has every page, action and route marked **built**, with zero mocked or missing
- [ ] `grep -r "TODO(backend)" web/src` returns nothing; the inventory check passes in CI
- [ ] `npm run build:cloudflare:production && npm run guard:build` passes (no `kien-mock-`, `lib/mock` or seed data in the bundle)
- [ ] Every e2e-live spec in 4.6 passes locally against the real backend **and** on the live hosts (Lane C run)
- [ ] Storage: R2 upload and download, ClamAV scan and quarantine, encryption at rest, retention rule, plus client data export and deletion, all proven
- [ ] Email works live: invite, reset, magic link, report-ready (from the verified Resend domain)
- [ ] Invoicing, client onboarding, checklist N/A ordering and undo, report edit, finalize and reopen, and the client report view all work live
- [ ] Auditor portal at `auditor.kiensolutions.com` and client portals on each pilot firm host work; a firm A user is refused on firm B's host

**Security and authentication** (S-01 to S-24 plus S-CI)
- [ ] Every row in 4.5 has a passing test or command and a file in `docs/security/evidence/`
- [ ] No open High or Critical finding from any scanner

**VPS (Lane C)**
- [ ] Hardened: keys only, no root login, ufw allows only 22, 80 and 443 (external nmap), fail2ban, unattended-upgrades, swap
- [ ] Stack healthy: Caddy (valid TLS), Postgres 16 with least-privilege roles, migrate, api, worker, ClamAV; memory within budget after 30 min (`docker stats`)
- [ ] `ai-adapter` present but `AI_ENABLED=false`
- [ ] Backups: restic to the object-locked R2 bucket; timers enabled; restore drill and lock drill PASS on real R2; fresh-box restore of a synthetic engagement PASS
- [ ] Deploy and rollback scripts used at least once each; RELEASES row recorded
- [ ] `api.kiensolutions.com` serves from the new VPS; the old server is untouched

**Readiness**
- [ ] `docs/readiness/STATUS.md` exists with all 45 items; every agent-owned Phase 2–4 item that Stage 1 covers is Done with evidence. Owner, attorney and Quentin items are listed as open

When every box is ticked, Slave Kien reports G1 to Abdullah with links. Stage 2 then starts.

---

## Part 7: Stage 2, security-skill audit in Claude Code (run by Abdullah or through Claude)

### 7.1 Verified free and open-source security skills and tools

All were checked on 2026-11-09 through the GitHub API (repo exists, not archived, license read) or the repo README.

| Name | URL | License | What it gives us | Install (from the repo README) |
|---|---|---|---|---|
| **Claude Code `/security-review`** (built in) and **claude-code-security-review** GitHub Action | https://github.com/anthropics/claude-code-security-review | MIT | Security review of pending changes. The README says Claude Code ships `/security-review` by default. It can be customized by copying `.claude/commands/security-review.md` into the project. The **Action** runs on PRs but needs an Anthropic API key (**paid API usage**), so the Action is optional | Run `/security-review` in Claude Code. Optional custom version: copy `.claude/commands/security-review.md` |
| **Trail of Bits skills** | https://github.com/trailofbits/skills | CC-BY-SA-4.0 | Relevant plugins: `static-analysis`, `insecure-defaults`, `sharp-edges`, `differential-review`, `supply-chain-risk-auditor`, `agentic-actions-auditor` (GitHub Actions), `entry-point-analyzer`, `audit-context-building`, `variant-analysis`, `fp-check`, `vulnerability-triage-brocards`, `semgrep-rule-creator`, `modern-python`, `property-based-testing`, `post-patch-validation` | `/plugin marketplace add trailofbits/skills`, then `/plugin menu` |
| **Sentry skills** | https://github.com/getsentry/skills | Apache-2.0 | `security-review`, `gha-security-review`, `security-model`, `skill-scanner` (checks other skills before you trust them), `find-bugs`, `code-review`, `claude-settings-audit` | `claude plugin marketplace add getsentry/skills`, then `claude plugin install sentry-skills@sentry-skills` |
| **OWASP security skill** (agamm) | https://github.com/agamm/claude-code-owasp | MIT | OWASP Top 10 (2025), ASVS and agentic-AI security guidance as a Claude Code skill | `/plugin marketplace add agamm/claude-code-owasp`, then `/plugin install owasp-security@agamm` |
| **Semgrep skills** | https://github.com/semgrep/skills | Semgrep Rules License v1.0 (free to use; restricts offering it as a competing service) | `code-security`, `llm-security`, `semgrep` skills | `npx skills add semgrep/skills` |
| **Cloudflare skills** | https://github.com/cloudflare/skills | Apache-2.0 | No dedicated "security audit" skill. Relevant pieces: `workers-best-practices` (Workers secrets, bindings, headers), `wrangler`, `cloudflare-one` (Zero Trust), `turnstile-spin` (bot protection on sign-in), `nextjs-on-cloudflare` | `/plugin marketplace add cloudflare/skills` |
| **OWASP ASVS 5.0** (checklist) | https://github.com/OWASP/ASVS (5.0 folder includes `OWASP_Application_Security_Verification_Standard_5.0.0_en.pdf`) | CC-BY-SA-4.0 | Level 2 checklist to map Kien's controls against | Reference |
| **OWASP Cheat Sheet Series** | https://github.com/OWASP/CheatSheetSeries | CC-BY-SA-4.0 | Session management, CSRF, authentication, file upload, multi-tenant, logging and secrets cheat sheets | Reference |
| **OWASP WSTG** (testing guide) | https://github.com/OWASP/wstg | CC-BY-SA-4.0 | Manual and DAST test cases for the live site | Reference |
| **OWASP ZAP** (DAST scanner) | https://github.com/zaproxy/zaproxy | Apache-2.0 | Baseline scan of the live hosts | `docker run --rm -t ghcr.io/zaproxy/zaproxy:stable zap-baseline.py -t https://auditor.kiensolutions.com` |
| Semgrep CE engine | https://github.com/semgrep/semgrep | LGPL-2.1 | Engine behind the Semgrep skills and CI | `pip install semgrep` |
| Semgrep community rules | https://github.com/semgrep/semgrep-rules | Semgrep Rules License | Rule packs | used by `--config p/...` |
| gitleaks | https://github.com/gitleaks/gitleaks | MIT | Secret scan | binary |
| trufflehog | https://github.com/trufflesecurity/trufflehog | AGPL-3.0 (fine to use as a tool) | Verified-secret scan | binary |
| Trivy | https://github.com/aquasecurity/trivy | Apache-2.0 | Vulnerability, secret, misconfiguration and container scan | binary or action |
| Bandit | https://github.com/PyCQA/bandit | Apache-2.0 | Python static security | `uvx bandit` |
| pip-audit | https://github.com/pypa/pip-audit | Apache-2.0 | Python dependency CVEs | `uvx pip-audit` |
| zizmor | https://github.com/zizmorcore/zizmor | MIT | GitHub Actions workflow security | `uvx zizmor` |
| hadolint (optional) | https://github.com/hadolint/hadolint | GPL-3.0 (fine as a tool) | Dockerfile lint | binary |
| CodeQL | https://github.com/github/codeql-action | MIT (action), but **code scanning on private repos needs paid GitHub Code Security** | Not used | — |

Not found or not usable: `semgrep/mcp` is **archived** (use `semgrep/skills` or the CLI). `anthropics/skills` has no security-specific skill and no repo-level license file.

Safety note: run Sentry's `skill-scanner` (or read each `SKILL.md`) on every third-party skill before enabling it. Skills are code and prompts from outside sources.

### 7.2 Stage 2 Claude Code prompt

Saved as [STAGE-2-SECURITY-AUDIT-PROMPT.md](STAGE-2-SECURITY-AUDIT-PROMPT.md).

---

## Part 8: Owner inputs (as few as possible)

Stage 1:
1. **VPS:** received. Public IP `135.148.219.175`, hostname `vps-8087ef2d`, Ubuntu 26.04, 2 vCPU, 3.7 GiB. Username and one-time password stay in the secure form / secret box only (never paste them into the repo or chat).
2. **R2:** the account ID plus a documents token and a backups token, or a yes to Slave Kien creating them through the Cloudflare connector **[unverified that it can]**. Store the restic password Slave Kien generates in your password manager.
3. **DNS yes:** point `api.kiensolutions.com` at the new VPS; add `auditor.` and the pilot firm hosts.
4. **Cloudflare API token** for kiensolutions.com (Workers Scripts Edit and DNS Edit).
5. **Resend** API key and a verified sending domain.
6. **Code lanes:** both Stage 1 code lanes run in **OpenAI Codex cloud**. Each lane merges its own PRs on green with merge commits. No Cursor coding agent and no Claude for Stage 1 code work. (Stage 2 security audit and Stage 3 AML engine still run in Claude, after their gates.)

Stage 2: your sign-off (G2). The optional claude-code-security-review Action would need an Anthropic API key, which is paid. Skip it unless you want it.

Stage 3: an OpenRouter key with a $0 limit, and approval of the free-model allowlist.

Not needed: GitHub deploy secrets or SSH deploy key (Slave Kien deploys), a GHCR token (images are built on the host), or CodeQL (paid for private repos).

---

## Part 9: Honest time estimate

| Work | Estimate | Notes |
|---|---|---|
| Phase 1 merges (#90, #37, #40), image fix, doc corrections | 2–4 h | Mostly done already |
| #45 portals and security review | 0.5–1.5 days | Large, security-sensitive |
| S-CI security workflow, plus fixing what it finds first | 3–6 h for the workflow; findings unknown | First scans often turn up dependency bumps |
| Deploy code (L1-3) and runbooks | 4–6 h | |
| VPS bring-up C0–C9 | 3–5 h of work once access and keys arrive; DNS and TLS can add waiting | Needs owner inputs 1–5 |
| Product inventory (L1-5) | 2–3 h | |
| **Backend routes for about 20 mocked contract groups (L2-6) plus wiring (L1-7) plus about 30 e2e-live specs** | **3–6 working days** of agent time | The bulk of Stage 1 |
| Security proof suite S-01 to S-24 with evidence | 1–2 days (overlaps with the above) | |
| **Stage 1 total** | **about 4–8 days wall-clock** with two code lanes plus Slave Kien running continuously | The 5-hour window covers Phase 1, S-CI, the deploy code, the VPS bring-up and the inventory, plus the first backend route groups |
| Stage 2 | 0.5–1.5 days, plus your review | Depends on how much the scans find |
| Stage 3 (engine) | 2–4+ weeks of iteration | Includes the two-week free-model trial |

**In the next 5 hours, realistically:**
- #90, #37 and #40 merged
- the image fixed
- `security.yml` running
- deploy code merged or in review
- the VPS hardened and the stack healthy (if access comes soon)
- the inventory published
- the first one or two backend route groups (firm settings, checklist and documents) in PRs

These will **not** be done in 5 hours: #45, full wiring, all e2e-live specs, and G1.

---

## Part 10: Launch files

- Code Lane 1 prompt: [LANE-1-PROMPT.md](LANE-1-PROMPT.md)
- Code Lane 2 prompt: [LANE-2-PROMPT.md](LANE-2-PROMPT.md)
- Stage 2 prompt: [STAGE-2-SECURITY-AUDIT-PROMPT.md](STAGE-2-SECURITY-AUDIT-PROMPT.md)
- Stage 3 (engine) prompt: written only after G2. The v1 Lane A items A1–A8 in [PLAN.md](PLAN.md) 3.7 are the starting scope, to run in Claude.

How Slave Kien launches the lanes:
- Start each lane in **OpenAI Codex cloud** on `abdullah-kynetic/ains-platform`, `main`. Paste the matching prompt under `docs/lanes/`, then a line `===PLAN===`, then this file. Each Codex lane merges its own PRs on green with merge commits. Codex has no VPS/SSH access; Slave Kien alone operates `135.148.219.175`.
- Watch each agent at the hourly checkpoints. Re-launch one if it stops before its done-list is complete.
