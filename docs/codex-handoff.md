# Codex handoff: build Kien up to (but not including) the AI features

Paste the section "Prompt" into Codex. Everything else in this file is reference for Abdullah.

## Prompt

You are working in `abdullah-kynetic/ains-platform` for Abdullah Ahmed, founder of Kien Solutions. **Kien** is the product: workflow software for independent AML testing of broker-dealers under FINRA Rule 3310, with an auditor portal and a client portal. The partner who approves findings and signs reports is **Quentin Koch**. Always spell it **Quentin**; "Quinton" is an old, wrong spelling.

Abdullah is not a developer. Explain things in plain English, keep reports short, lead with the answer, and mark anything you inferred or did not verify.

### First, read
`CLAUDE.md`, `AGENTS.md`, `DESIGN.md`, `docs/DESIGN_SYSTEM.md`, `docs/frontend-inventory.md` (the backend handoff: every screen, route, and every `TODO(backend)` mocked call with its data shape), `docs/kb/00-INDEX.md`, `docs/kb/15-roadmap-build-order.md`, `docs/kb/19-open-questions.md`, `docs/SECURITY.md`, `docs/TESTING.md`. Read the code before changing it.

### Current state (as of `main`)
- Merged to `main`: invoicing, reversible and direct N/A, editable reports, first-sign-in walkthrough, shadcn layout, and the neutral black-and-white redesign with all new auditor screens.
- The new auditor screens (clients, engagement workspace tabs, workpapers, samples, findings, report builder and sign-off, independence, firm settings, notifications, search) and the client "Responses requested", Report and Invoices pages run on a **typed mock layer** in `web/src/lib/api/*` over `web/src/lib/mock/*`. They have no backend yet.
- **Web sign-in is restored** (PR for IMPL-4). The synthetic demo build still skips it. Hostname-to-audience mapping is in `web/src/lib/audience.ts`.
- Some older e2e tests are broken by the redesign and removed auth.
- `docs/kb/*` pages still describe the old cream and ochre look.

### Hard rules (never break)
1. SAR material never goes to any AI model. **Do not build any AI feature in this task** (no model calls, no model SDKs; `tests/test_workflow_boundary.py` must keep passing).
2. Synthetic data only. Never request or use real client documents.
3. No secrets in chat, code, commits, logs or screenshots. Use environment variable names only. Never read or print `.env`.
4. Shared OVH server: never touch n8n, Twenty CRM or the client portal. Kien lives only in `/opt/kien`, compose project `kien`. Do not run anything on the server unless explicitly told.
5. Git: commit as `abdullah-kynetic <211030198+abdullah-kynetic@users.noreply.github.com>`. **Real merge commits only. No rebase, no squash, no force-push.** Never push to `main` directly; work on branches.
6. Preview first. Deploy only to preview and layout (`kien-signin-preview`, `kien-shadcn-preview`) and only when a step says so. **Never deploy to live** (`kien-demo-live`). Never run production migrations. Do not delete data or send external messages.
7. Keep the approved look (neutral black-and-white, see `DESIGN.md`). Ink `#33405C` only for logo, primary buttons, active nav and focus; ochre only for deadlines; red/amber/green only as status pills. No gradients, glass or cream.
8. Clients never see audit findings. Client-visible intake feedback is document-level only (unreadable, wrong period or document, missing pages). Only auditor-released "Responses requested" text (title and request) reaches the client.
9. Humans approve findings and sign reports. Code never marks a finding final or a report signed without an auditor action. Every finding needs a document and page citation.
10. Tenant isolation: every tenant-owned query filters by `firm_id`; auditors see only assigned engagements. **Add a cross-tenant denial test for every new API path.** UI role gates are not authorization.
11. `data/checklist/aml_bd_v1.yaml` is the canonical source of the 34 request IDs. Keep web status values aligned with `app/checklist.ClientStatus`. Leave rubric placeholders empty for Quentin.
12. Costs as low as possible. Do not add paid services without asking.
13. Never claim a test or check passed unless you ran it. Report exact commands and results.
14. Do not decide product or spending questions. Collect them in a "Decisions needed" list and continue with a safe default.

### Verified commands
- Backend (repo root): `uv sync --frozen`, `uv run ruff check .`, `uv run pytest -q`
- Web (`web/`): `npm ci`, `npm run lint`, `npm run typecheck`, `npm run test:unit`, `NEXT_PUBLIC_USE_MOCKS=true npm run build`, `npm run build:cloudflare`, `npm run test:e2e`
- Local Postgres 16: `docker compose up -d`. Migrations are Alembic and must be additive and reversible; confirm parity on a real PostgreSQL.

### How to work
Small slices, one branch and one pull request per slice, stacked in the order below. Each PR: what changed, why, the exact checks run with results, screenshots for UI changes (desktop light, desktop dark, phone), and limitations. If GitHub will not let you open PRs, push the branches and list them for Abdullah. Do not wait for review between slices unless a step says "stop and ask". Update `docs/frontend-inventory.md` and the relevant docs as you go.

### Commit style
Commit in small, real steps. Follow `docs/commit-plan.md`: one logical change per commit, each building and passing its own tests. No empty, filler or whitespace-only commits. Open one PR per slice.

### Scope, in order

**Phase 1: clean up (small)**
1. Fix the broken e2e tests (activity, accessibility, header-sidebar, redesign, checklist-na, questionnaire and others) so `npm run test:e2e` passes, keeping the intent of each test. Remove tests only for features that were deliberately removed (web sign-in).
2. Fix the "Quinton" to "Quentin" spelling in current-context text (README, AGENTS, PRD, deploy-aws, build-handoff, `app/checklist/catalog.py` docstring). Keep it in quoted history. Leave test fixtures such as the Egnyte "quintonsfirm" sample alone.
3. Refresh the `docs/kb/` pages and `docs/ARCHITECTURE.md` / `PRD.md` / `SECURITY.md` that still describe the cream/ochre look, the old PR state, or removed screens. Reconcile OVH vs AWS conflicts.

**Phase 2: backend for the new audit screens (the biggest block)**
Implement the routes in `docs/frontend-inventory.md`, matching the shapes in `web/src/lib/api/types.ts`. Build each as its own slice with models, additive migration, endpoints, firm and assignment scoping, audit-log entries, and tests including cross-tenant denial. Then replace the matching mock function in `web/src/lib/api/*` with a real `apiRequest` call (keep a mock fallback only under `USE_MOCKS`). Suggested order:
1. Clients, contacts, engagement summaries.
2. Checklist test results (Pass, Partial, Fail, Does not apply; N/A counts as resolved) and documents listing.
3. Workpapers (reviewer must differ from preparer; editing clears review), samples.
4. Findings (draft, approved, issued, responded, closed; citation required; only an auditor action moves a finding) and the "request a response" release that creates the client-visible response request.
5. Report assembly from approved findings, Word and PDF export from `templates/report`, and the report fingerprint.
6. Independence record, second-reviewer approval, partner sign-off (server computes the fingerprint and records the signature), mark complete.
7. Firm settings: team and roles (cannot remove the last partner), branding (logo to object storage), rubric, request-list templates (introducing, retail, self-clearing, custom).
8. Notifications, global search scoped to assigned engagements.
9. Client side: response requests (title and request text only; server must never join finding fields into the client payload), signed reports, invoices.
Stop and ask Abdullah before changing an existing table in a non-additive way.

**Phase 3: restore auth (before any live deploy or real data)**
Done on the IMPL-4 branch: sign-in, MFA enrolment and recovery, invitation, account setup, reset and sign-out are restored, a role that does not match the host's audience gets the wrong-portal screen, and `npm run test:e2e:live` exercises it against a local backend. Not deployed.

**Phase 4: security hardening** (roadmap item 2)
Malware scan on uploads with a quarantine state (e.g. a ClamAV sidecar), general API rate limits and login lockout, an operations runbook, scheduled off-site backups, and a restore drill. Document everything in `docs/`. Do not touch the live server; write the scripts, config and instructions, and list what Abdullah must run.

**Phase 5: invoicing follow-ups and Stripe** (roadmap item 1)
Overdue reminders and follow-ups; Stripe payment links behind a feature flag that is off by default; webhook records a payment as an invoice event. Needs a Stripe account decision: build against test mode only and list the decisions needed.

**Phase 6: AWS migration preparation** (roadmap item 4)
Follow `docs/kb/14-aws-migration-plan.md`: infrastructure as code, config and runbooks only. Do not apply anything or create AWS resources. List the inputs Abdullah must provide.

### Do not do
Any AI feature (intake sorting, FINRA chatbot, model calls). Any live deploy. Anything on the shared OVH server. Merging to `main` (Abdullah reviews). Inventing legal text (privacy policy, terms) or audit criteria; those need the attorney and Quentin.

### Report format
After each slice: branch and PR, what changed (plain English), exact commands run with results, screenshots, what is not done, and "Decisions needed" and "Needs Quentin / attorney". End with a one-screen status of all phases.

## Reference for Abdullah

- **What Codex will not do:** deploy live, touch the OVH server, build AI, or merge to `main`.
- **Decisions Codex may ask about:** can a client undo an N/A the auditor set; auditor hostname and Cloudflare Access; Stripe account and payment methods; AWS single server vs managed database; budget cap; retention and backup targets.
- **Needs other people:** Quentin (rubric wording, allowed evidence, report template wording, severity logic); the attorney (written approval of Anthropic and OpenAI, Reg S-P terms, privacy policy and terms wording).
