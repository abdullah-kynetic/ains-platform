# Lane 2 handoff for Claude Code

Snapshot verified Tuesday, Nov 10, 2026, 11:45 AM Pacific Time (America/Los_Angeles), against GitHub and `origin/main` at `ddba2df` (merge of [#101](https://github.com/abdullah-kynetic/ains-platform/pull/101)). Codex ran out of usage before it could finish this handoff; Slave Kien wrote it from the lane chats and then confirmed PR and branch state. Update the Done and In progress sections in each of your PRs so any agent can continue.

## Start here

Read these first, in order:

1. `CLAUDE.md` and `AGENTS.md`
2. `docs/BUILD-PLAN.md` (Part 4.4, items L2-5 through L2-10)
3. This file (`docs/handoff/LANE-2-HANDOFF.md`). If it is not on `main` yet, read it from branch `handoff/lane-2`.
4. `docs/STATUS.md`, especially **Requests to Lane 2** (quoted below). That table is the contract list for the routes Lane 1 is waiting on.
5. `docs/frontend-inventory.md` and `web/src/lib/api/types.ts` (the contract; do not edit `web/src/lib/api/**` unless you open a `CONTRACT-CHANGE:` PR and also update the inventory)
6. `tests/route_inventory.txt`, `tests/test_client_view_allowlist.py`, `tests/test_workflow_boundary.py`, `tests/test_route_isolation.py`

First commands:

```bash
git fetch origin --prune
git checkout main
git pull --ff-only origin main
git log origin/main --oneline -20
```

Then confirm which of [#102](https://github.com/abdullah-kynetic/ains-platform/pull/102), [#103](https://github.com/abdullah-kynetic/ains-platform/pull/103), and [#104](https://github.com/abdullah-kynetic/ains-platform/pull/104) have merged. Start at the first unfinished item in **Next**. Work autonomously and nonstop, in small PRs, until every item is merged or recorded as `BLOCKED(owner)`.

Allowed edit paths: `app/**`, `migrations/**`, `tests/**` (not Lane 1's `tests/test_deploy*.py`, `tests/test_image_workflow.py`, `tests/test_ci_*.py`, `tests/test_db_roles.py`), `scripts/e2e_seed.py`, `app/pilot_seed.py`, `web/src/components/tenant/**`, `web/src/lib/tenant*.ts`, `web/src/lib/audience*.ts`, plus `docs/STATUS.md`, `docs/readiness/**`, `docs/frontend-inventory.md`, `docs/security/evidence/app-*.md`, `docs/evidence/**`, `docs/kb/**` except `kb/10` and `kb/13`, and this handoff file. Never edit `.github/**`, `deploy/**`, `Dockerfile`, `pyproject.toml`, `uv.lock`, `web/src/lib/api/**`, other `web/**`, `audit_engine/**`, or `ai_adapter/**`.

## Done

- **L2-0** — Postgres service in CI. [#90](https://github.com/abdullah-kynetic/ains-platform/pull/90) merged.
- **L2-1** — Portal API URL rebuild. [#92](https://github.com/abdullah-kynetic/ains-platform/pull/92) merged; original #37 closed as superseded. Production browser artifact embeds `https://api.kiensolutions.com`.
- **L2-2** — Report-ready email rebuild. [#93](https://github.com/abdullah-kynetic/ains-platform/pull/93) merged; original #40 closed. Mail failure does not undo sign-off; findings, report content, addresses and keys are not logged.
- **L2-3** — Client portal rebuild. [#96](https://github.com/abdullah-kynetic/ains-platform/pull/96) merged (commit `9a8a10a`); original #45 closed. Confirmed merged on GitHub and in `git log origin/main`. Some older paragraphs in `docs/STATUS.md` still talk about #96 as open; treat those as stale.
- **L2-4** — Status-doc corrections. [#95](https://github.com/abdullah-kynetic/ains-platform/pull/95) merged.
- **L2-5 S-01 through S-06** — Auth proofs. [#99](https://github.com/abdullah-kynetic/ains-platform/pull/99) **confirmed merged** Monday, Nov 9, 2026, 5:07 PM Pacific Time (America/Los_Angeles) (`merged_at` 2026-11-10T01:07:21Z, merge commit `083daba`). Branch was `lane2/l2-5`. Evidence in `docs/security/evidence/app-s-01.md` through `app-s-06.md`. PR body: 15 security tests passed; broader auth/reset/API suite 70 passed. Fixes shipped: auditor sessions are revoked when MFA is disabled, and on role or firm change (including rollback). Sign-out remains available after MFA disablement. Legacy tokens without role/firm claims need a fresh sign-in after deploy. No model, frozen-path, web-source, server or deployment changes.
- Related Lane 1 merge that unblocked the portal: [#98](https://github.com/abdullah-kynetic/ains-platform/pull/98) (live fixture host + current migration head). Not a Lane 2 item.

## Update 2026-11-10 (Claude Code, Lane 2)

- **GitHub Actions outage.** From about 19:46 UTC every job on every new push fails in 1-2 seconds
  with no steps (CI and Security, even on a docs-only PR). Re-run did not help. Nothing can be
  merged until it recovers; this is not a code failure. Check the account's Actions billing and
  spending limit first.
- **#102** now carries the `krb5-libs` pin cherry-picked from #103 (commit `40e2fd5`; Dockerfile
  exception recorded here) and main merged in. Local: ruff clean, 535 passed, 1 skipped
  (PostgreSQL tests cannot run locally; CI is authoritative). Merge it when CI and Security are green.
- **Workflow PR** (branch `claude/project-thread-grvxp5`, stacked on #102): steps 1-9 of Next 3 in
  one tested slice (dispatch, reasoned N/A, document numbers, links and submit, issue flags and
  threads, progress, report confirmation, invoice gate, stages). Contract for Lane 1:
  `docs/kb/23-workflow-api.md`. Migration `a120_workflow_routes`.
  Open decisions for Abdullah are at the end of that file.
- **S-19** built on branch `lane2/s-19` (stacked on the workflow PR): authorized download routes, 60 s presigned links, evidence `app-s-19.md`. Live anonymous-403 check is Lane C.
- Actions recovered at 20:43 UTC; #102 Security is green.
- **Merged to main (green CI and Security):** #102, #106 (workflow routes), #107 (S-19), #104 (S-12).
- **Done: L2-6a** (branch `claude/project-thread-grvxp5`): practice team, branding, rubric,
  request templates. Migration `a121_practice_routes`. Contract and decisions:
  `docs/kb/24-practice-api.md`. Local: ruff clean, 583 passed, 1 skipped (PostgreSQL tests need CI).
- **Merged:** #108 (L2-6a practice routes).
- **Done: L2-6b** (branch `claude/project-thread-grvxp5`): `GET` and `PATCH`
  `/auditor/engagements/{id}/checklist-tests`, migration `a122_checklist_conclusions`. The
  conclusion is the auditor's own entry; nothing derives it and clients never see it. N/A rows
  (conclusion `na` or accepted N/A) sort last with ids unchanged. Documents need no new route:
  `listDocuments` already reads the live auditor workspace, which carries document numbers.
- **Done: L2-6c** (branch `lane2/l2-6c-workpapers-samples`): workpapers (save, independent review)
  and sample sets, migration `a123_workpapers_samples`. Contract and decisions:
  `docs/kb/25-workpapers-samples-api.md`.
- **Merged:** #110 (L2-6c workpapers and samples).
- **Done: L2-6d** (branch `claude/project-thread-grvxp5`): findings CRUD and status, explicit
  response-request release, client response requests and one reply. Migration
  `a124_findings_responses`. Contract and decisions: `docs/kb/26-findings-api.md`.
- **Done: L2-6e** (branch `lane2/l2-6e-report-draft`, stacked on #111): assembled report draft,
  section edits, real `.docx` and PDF downloads. Migration `a125_report_section_edits`. Contract and
  decisions: `docs/kb/27-report-draft-api.md`. Client reports wait for sign-off (L2-6f).
- **Merged:** #112 (L2-6e report draft).
- **Done: L2-6f** (branch `lane2/l2-6f-signoff`): independence, reviewer approval, partner
  signature with server-computed fingerprint, completion, client signed report. Migration
  `a126_engagement_signoffs`. Contract and decisions: `docs/kb/28-signoff-api.md`.
- **Merged:** #113 (L2-6f independence and sign-off).
- **Done: L2-6g** (branch `lane2/l2-6g-activity`): per-engagement activity, derived notifications
  with read marks, search. Migration `a127_notification_reads`. Contract and decisions:
  `docs/kb/29-feed-api.md`.
- **Merged:** #114 (L2-6g activity, notifications, search).
- **Done: L2-6h** (branch `lane2/l2-6h-client-invoices`): client invoice list plus overdue-invoice
  notifications. No migration. Contract and decisions: `docs/kb/30-client-invoices-api.md`.
  This finishes L2-6.

- **Done: L2-7** (branch `lane2/l2-7-retention`): R2 upload fix (no `VersionId`), retention rule,
  firm data export, confirmed erasure of stored files (operator CLI, no HTTP route). Contract and
  decisions: `docs/kb/31-retention-export-erasure.md`. Live R2 and ClamAV checks are Lane C.
- **Done: L2-8** (branch `lane2/l2-8-signed-report-confirm`): the signed report can now be
  confirmed by the client (unlocks invoicing), plus one end-to-end journey test. Contract and
  decisions: `docs/kb/32-report-confirmation-and-journey.md`. Existing flows re-run, all pass.
- **Merged:** #116 (L2-7). **Next:** L2-9 (pilot seed, PR #118), L2-10 (readiness tracker).

## In progress

### 1. PR #102 — S-07 through S-15 except S-12 (open, not mergeable until the image scan is green)

- URL: https://github.com/abdullah-kynetic/ains-platform/pull/102
- Title: "Prove tenant and client-field isolation with private configuration"
- Branch: `lane2/l2-5-rest`, head `2c73f677bf8e31f214afda5b34a015c8ce443473`, base `main` at `ddba2df`
- Coverage: executable proofs for S-07, S-08, S-09, S-10, S-11, S-13, S-14 and S-15. Database URLs and demo passwords are `SecretStr`; connection URLs unwrap only inside SQLAlchemy/Alembic adapters; demo passwords load through `app/config.py`.
- Local results recorded in the PR body: `uv run pytest -q tests/security` 53 passed; focused metadata/field/config command 10 passed; full `uv run pytest -q` 530 passed, 13 skipped, one existing Starlette deprecation warning. Codex claimed an independent review passed. There are **no GitHub review objects** on the PR itself.
- Hosted checks on head `2c73f67`, verified 11:23 AM Pacific Time (America/Los_Angeles) Nov 10: **Python lint and tests**, **Web lint, typecheck, and build**, and Security jobs **zizmor, trufflehog, gitleaks, bandit, semgrep, pip-audit, trivy-fs, npm** all succeeded. **Security (trivy-image) failed** (completed 11:22 AM Pacific Time). `mergeable_state` is `unstable`. Do not merge while that job is red.
- Cause of the scan failure, also found by Lane 1 on [#103](https://github.com/abdullah-kynetic/ains-platform/pull/103): High Kerberos CVEs in `krb5-libs` in the unchanged Alpine base. The fix is `krb5-libs` 1.22.3-r0. #103's commit `25a90fe` installs that minimum with `apk add --no-cache --upgrade 'krb5-libs>=1.22.3-r0'` in the Dockerfile. It does **not** bump the `python:3.12-alpine` digest. On #103, **trivy-image and every other check passed** (trivy-image completed 11:22 AM Pacific Time). #103 is Lane 1's PR; do not merge it yourself.
- What's left: get trivy-image green, then merge #102 with a merge commit. Preferred path: wait for #103 to land (it is already all-green), then `git merge origin/main` into `lane2/l2-5-rest` and re-run checks. If #103 is still open and this is blocking you, cherry-pick only `25a90fe` onto #102 (merge commits only; no rebase or force-push) and record the Dockerfile ownership exception in `docs/STATUS.md`. The Lane 2 prompt normally forbids editing `Dockerfile`.
- S-16, S-17 and S-18 need Lane 1 / Lane C evidence and are not claimed complete.

### 2. PR #104 — S-12 log privacy (open, stacked on #102)

- URL: https://github.com/abdullah-kynetic/ains-platform/pull/104
- Title: "Withhold private content from application logs"
- Branch: `lane2/l2-5-logging`, head `a5b877c8664ce3978ff46dc02a550d9641603ca5`
- Base is `lane2/l2-5-rest` (`2c73f67`), **not** `main`. Opened 11:23 AM Pacific Time (America/Los_Angeles) Nov 10. 3 commits, +194 / −6, 6 files. Codex had only pushed the branch when usage ran out; the PR exists now.
- Behavior: rejected uploads keep only hashes in audit metadata; logs and telemetry drop private paths, queries, exception text, filenames and raw scanner signatures, while keeping bounded operational metadata. Tests assert logs never contain invitation tokens, query values or exception text.
- Local results recorded in the PR body: focused privacy suite 32 passed; Ruff passed. Hosted on head `a5b877c`: Python lint and tests, web lint/typecheck/build, and the non-image Security jobs succeeded; **trivy-image failed** for the same base-image CVE. `mergeable_state` is `unstable`.
- What's left: do not merge onto `main` until #102 has landed (or retarget the base after #102 merges). Re-apply the same image-scan fix after #102/#103, run the full gate, then merge on green. Evidence file: `docs/security/evidence/app-s-12.md`.

### 3. S-19 download authorization — not started

No branch or PR. This is the last remaining Lane 2 security-proof item after #102 and #104.

## Next

Work in this order. For every new or changed route: enforce `firm_id` and auditor assignment; add a cross-tenant denial test with real foreign or unassigned IDs; write the audit chain on state changes; match `web/src/lib/api/types.ts`; add the route to `tests/route_inventory.txt`; extend `tests/test_client_view_allowlist.py` where a client can call it. Clients never see findings (never join or serialize finding fields). Keep `tests/test_workflow_boundary.py` passing. Additive Alembic revisions only, with upgrade/downgrade coverage in a `*_postgres.py` test (CI Postgres is authoritative if local `initdb` cannot run).

### 1. Get #102 merged

Acceptance: hosted CI and every Security job, including **trivy-image**, are green; independent verify recorded; merged with a merge commit.

Tests (already expected to pass; re-run after the image-scan fix):

```bash
uv sync --frozen && uv run ruff check .
uv run pytest -q tests/security
uv run pytest -q
```

### 2. Finish S-12 (#104) and S-19

**S-12.** After #102 is on `main`, merge `origin/main` into `lane2/l2-5-logging` (or retarget #104), get trivy-image green, and merge. Acceptance: logs and Sentry contain no document content, SAR terms, tokens, emails, query values or exception text; rejected-upload audit metadata is hashes only; evidence file updated with the command, result and commit.

```bash
uv run pytest -q tests/security/test_log_scrubbing.py tests/security
uv run ruff check . && uv run pytest -q
```

**S-19.** New branch from updated `origin/main`. Acceptance: every download is authorized on that request; presigned links are short-lived; a cross-tenant or unassigned download is denied; evidence at `docs/security/evidence/app-s-19.md`.

```bash
uv run pytest -q tests/security/
```

S-16, S-17 and S-18 stay with Lane 1 / Lane C; do not mark them done.

### 3. Quentin's workflow backend routes (blocks Lane 1)

This is the critical path. Build the backend for Quentin's real workflow before the remaining L2-6 groups that are not on this list. Mirror the workflow online, in order. Item status values: not started / submitted / needs info / accepted / N/A. N/A items sort last and keep their original numbers; undo restores the previous state. Invoice is issued only after client confirmation; the auditor marks paid; do not add card payments (parked until a provider is chosen).

| Step | Behavior |
| --- | --- |
| Checklist send | Auditor sends the numbered checklist and records sent state/time. Engagement status becomes "Checklist sent". Initialization alone is not a recorded client dispatch. |
| Reasoned N/A | Client requests N/A with a required reason; auditor accepts or rejects. Pending / accepted / rejected states. Accepted N/A sorts last; numbers kept; undo restores the previous state. Do not auto-approve. |
| Stable document numbers | Every uploaded document gets a stable number the client and auditor can cite (for example `1.17`). |
| Item-to-document links + submit | Client links receipts to items ("Item 22: see 1.17, 1.18") and submits the item or checklist. |
| Per-document issue flags | Auditor flags a document as outdated, wrong year, incorrect, or missing, with a note. |
| Per-item request threads | Each flag creates a per-item request thread with replies and re-uploads until explicit resolution. Existing intake feedback is not this lifecycle. |
| Per-item status + progress | Status on each checklist line, plus a progress view for both sides. |
| Report finalize | Auditor writes and finalizes the report from accepted items (hash on finalize). |
| Client report confirmation | Client reviews and confirms the finalized report in the portal; confirmation is audit-logged. |
| Invoice gate | Invoice may be issued only after confirmation. Paid/unpaid state; auditor marks paid. No card payments. |
| Stage pipeline | Stages: Checklist sent, Client working, Under review, Info requested, Report drafting, Report sent, Confirmed, Invoiced, Paid. |

Acceptance: each route meets the per-route rules above; clients never see findings; `docs/STATUS.md` Requests to Lane 2 rows for these flows are satisfied.

```bash
uv run pytest -q tests/test_checklist_na.py tests/test_invoices.py tests/test_onboarding.py tests/test_report_workflow.py tests/test_password_reset.py tests/test_route_isolation.py tests/test_client_view_allowlist.py tests/test_responses_requested.py tests/test_workflow_boundary.py
uv run ruff check . && uv run pytest -q
```

Use a group-specific test module plus the isolation, allowlist and responses-requested tests in each PR, as in the plan: `uv run pytest -q tests/test_<group>.py tests/test_route_isolation.py tests/test_client_view_allowlist.py tests/test_responses_requested.py`.

### 4. Remaining L2-6 route groups

Small PRs, in plan order, skipping anything already delivered in step 3:

- (a) firm team, branding (logo stored in R2), rubric (criteria stay empty for Quentin), request templates. This unblocks Lane 1's live firm-settings CRUD on #103.
- (b) checklist tests and conclusions, engagement documents
- (c) workpapers and review (reviewer must differ from preparer), samples. Do not invent conclusions from human assessment values.
- (d) findings CRUD and status; response-request release for approved findings only; client response requests and replies (**never join finding fields**)
- (e) report draft, sections, `.docx` and PDF from `templates/report`; client reports only once signed
- (f) independence; sign-off (review, partner, complete; the server computes the fingerprint)
- (g) activity, notifications, search (assigned engagements only)
- (h) client invoices

Acceptance and tests: see L2-6 in `docs/BUILD-PLAN.md`. If a contract must change, update `docs/frontend-inventory.md` in the same PR and title it `CONTRACT-CHANGE: ...`.

### 5. L2-7 storage complete

Upload and download through R2 (S3 API); authorization checked on every download; only short-lived presigned links; ClamAV scan before a file becomes available (quarantine otherwise); SHA-256 fingerprints; a retention rule plus export and deletion of one client firm's data on request (readiness item 25). Live R2/ClamAV evidence is Lane C / Slave Kien; do not claim a live check you did not run.

```bash
uv run pytest -q tests/test_s3_storage.py tests/test_upload_scanning.py tests/test_document_ingestion.py tests/test_storage_retention.py
```

### 6. L2-8 remaining end-to-end flows

Email (invite, reset, magic link, report-ready), invoicing, client onboarding (invite, accept, set password, walkthrough), checklist N/A ordering, reports (edit, finalize with a hash, reopen), both portals and firm subdomains. Anything already shipped in step 3 should be regression-tested, not rebuilt.

```bash
uv run pytest -q tests/test_checklist_na.py tests/test_invoices.py tests/test_onboarding.py tests/test_report_workflow.py tests/test_password_reset.py
```

### 7. L2-9 demo seed (synthetic only)

`app/pilot_seed.py` (three synthetic firms with portal slugs, engagements, an auditor, and invitations sent through Resend; refuses `INVITATION_PREVIEW_ENABLED` in production; prints no tokens) and `scripts/e2e_seed.py` (everything Lane 1's e2e-live specs need). Both idempotent; synthetic names only. Add `tests/test_pilot_seed.py`.

```bash
uv run pytest -q tests/test_pilot_seed.py
```

### 8. L2-10 readiness tracker

`docs/readiness/STATUS.md`: all 45 readiness items, each with a status, an evidence link and an owner. Mark Done only with evidence.

## Requests to Lane 2 (from `docs/STATUS.md` on main)

Copied from main at `ddba2df` so a cold agent has it even if STATUS later moves. Re-read the live file before implementing; it is the contract. Existing types in `web/src/lib/api/types.ts` remain the contract for the listed route groups. A backend route must enforce firm ownership, assignment, role and workflow transitions; UI state is not authorization.

| Flow | Required route/behavior | Existing route limitation |
| --- | --- | --- |
| Checklist dispatch | Auditor sends the numbered checklist and records sent state/time | Initialization creates instances but is not a recorded client dispatch |
| Reasoned N/A | Client requests N/A with a required reason; auditor accepts/rejects; pending/accepted/rejected states, original item numbers, N/A last | Direct N/A auto-approves; questionnaire N/A review only covers conditional questions |
| Document numbering/linking | Stable document numbers such as 1.17; client links receipts to items and submits each item | Workspace exposes linked receipt metadata, not stable numbers or a client linking/submission mutation |
| Document issue threads | Atomic flag on a document (outdated, wrong year, incorrect, missing) creates an item request thread; replies and explicit resolution drive item status/progress | Existing intake feedback and item response release do not implement a per-document thread lifecycle |
| Findings/replies | Finding CRUD/status and explicit approved-finding response release; client allowlisted request list/reply | Existing item-based release is not the finding-based contract |
| Report | Engagement report draft/sections/docx and independence/reviewer/partner sign-off contracts | Separate `/auditor/reports` editor/finalize routes exist; engagement draft/sign-off contracts do not |
| Client confirmation/invoice | Client sees finalized report and confirms it; server allows invoice issuance only after confirmation; paid/unpaid state | Auditor invoice CRUD exists; no client confirmation gate or client invoices contract |
| Pipeline | Workflow stages include dispatch, client submission, issue resolution, report finalization, client confirmation and invoicing | Current six stages do not represent all of these transitions |
| Team/branding | Team invite/roles/removal and branding/logo file upload to API/object storage | `/auditor/firm/team` and branding contract routes absent |
| Rubric/templates | Partner-approved rubric and request-template CRUD | Contract routes absent; keep criteria empty |
| Testing/workpapers/samples | Checklist conclusions, workpapers/review and sample sets/results | Contract routes absent; do not translate human assessment values into invented conclusions |
| Notifications/search | Server-scoped notification/read and search contracts | Contract routes absent |

## Blockers and decisions

- **Image scan (active).** #102 and #104 fail Security (trivy-image) on High `krb5-libs` CVEs. #103 already has the proven one-line apk pin and a green image scan. Lane 2 does not merge Lane 1 PRs and does not normally edit `Dockerfile`.
- **#104 is stacked on #102.** Merge #102 first, then #104.
- **`Dockerfile` ownership.** Never edit it unless you are cherry-picking the already-proven #103 fix to unblock #102, and record that exception.
- **`deploy/` and compose** belong to Slave Kien. Do not touch them. [#100](https://github.com/abdullah-kynetic/ains-platform/pull/100) (L1-3 deploy code) is still open and is not yours.
- **No server access.** Never touch the old shared server `40.160.150.91`. The live VPS is `135.148.219.175`; you still have no SSH to it.
- **Frozen paths.** No edits to `audit_engine/**` or `ai_adapter/**` until Abdullah's Stage 2 sign-off. No model calls in Stage 1.
- **Synthetic data only.** No real client data. No secrets in the repo; never read `.env`; variable names only.
- **Card payments** are parked until Abdullah picks a provider. Auditor mark-paid only.
- **Live report-ready email** needs a Resend key from Abdullah for real delivery. The #93 code is already on main; do not claim live delivery without it.
- **BLOCKED(owner/attorney):** readiness item 41 vs `CLAUDE.md` rule 10 (vendor approval). Not a reason to stop the route work. Record, do not invent an answer.
- **S-16 / S-17 / S-18** are Lane 1 / Lane C evidence, not Lane 2 merge gates.
- **Git rules:** no rebase, no squash, no force-push; merge commits only. Merge your own PRs only when CI, Security and independent verify are all green. At most 3 fix attempts on the same failure; at most 2 independent-verify rounds. Commit as `abdullah-kynetic <211030198+abdullah-kynetic@users.noreply.github.com>`.
- **Spell it "Quentin".** Leave rubric criteria empty. Clients never see findings, only released "Responses requested". Only an auditor action approves findings or signs reports. No SAR material to any model; items AML-BD-017 and AML-BD-025 are metadata-only, human-only.

Decisions already made and shipped or agreed:

- Sessions are revoked when auditor MFA is disabled and when role or firm changes (#99).
- Database URLs and demo passwords are `SecretStr` (#102, not yet merged).
- N/A sorts last, original numbers are kept, undo restores the previous state; N/A is not auto-approved.
- The invoice is issued only after client report confirmation; the auditor marks it paid.

## Notes for Lane 1

- Quentin's workflow screens cannot be wired for successful live writes until the routes in **Next step 3** are on `main`. Until then, live mode should show the typed unavailable/error state, not synthesize success or fall back to mocks.
- [#103](https://github.com/abdullah-kynetic/ains-platform/pull/103) (firm settings + `krb5-libs` pin) is open and was all-green, including trivy-image, as of 11:27 AM Pacific Time (America/Los_Angeles) Nov 10. Merging it is the cleanest way to unblock #102's image scan. Lane 2 will not merge it. Firm CRUD, invitation delivery, logo object storage, last-partner protection and rubric approval still need L2-6(a) and the related routes; #103's live browser specs currently prove the unavailable state, not successful CRUD.
- Notifications and search page wiring can continue against the existing contract; the backend routes are L2-6(g) and are listed in Requests to Lane 2.
- Lane 1 owns `web/**` except the tenant files listed in Allowed edit paths, plus `web/package.json` and `web/wrangler.jsonc`. Preserve the build-time API URL helper from #92.
- Do not weaken portal host binding to make a fixture pass.
- If you change `types.ts`, tell Lane 2; Lane 2 matches that file and will not silently diverge.

## L2-10 readiness tracker (branch lane2/l2-10-readiness)

`docs/readiness/STATUS.md` lists all 45 items with status, evidence and owner. Lane 2 can still do items 18, 20, 21, 23 and 28 without anyone's input; 13, 16 and 33 wait on Abdullah and Lane C; 39 to 45 wait on G2.

## Loop reminder

From the Lane 2 prompt: branch `lane2/<item>` from `origin/main` (or reuse the named branch); catch up with `git merge origin/main`; smallest change; run the item tests, then `uv sync --frozen && uv run ruff check . && uv run pytest -q`; fix failures (max 3 attempts); open a PR with exact commands and results; independent verify (max 2 rounds); you merge on green with a merge commit; add a line to `docs/STATUS.md` and refresh this handoff's Done / In progress / Next. Never claim an unrun test passed. If Postgres cannot run locally, say so and rely on CI.
