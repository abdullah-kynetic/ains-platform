# Kien status (2026-11-09)

This page is the current status summary. It was checked against GitHub on 2026-11-09. Where a line says "not run", that check was not run.

## Where things stand

- **Code on `main`:** PRs #78 to #88 are merged. Web sign-in is restored (real `/auth/*` routes). Only the synthetic demo build (`NEXT_PUBLIC_USE_MOCKS=true`) skips sign-in.
- **Real client data:** none. Synthetic data only. The rule stays until the readiness checklist is complete and Abdullah changes it in writing. See [readiness checklist](readiness/readiness-checklist-2026-11-07.md).
- **AI:** the separate `ai_adapter/` skeleton exists on main, is off, and has an empty allowlist. The engine and adapter are frozen until Stage 2 sign-off. No model calls in Stage 1. Rule 10 and readiness item 41 disagree about OpenRouter approval; see [open questions](kb/19-open-questions.md).
- **Hosting plan (Abdullah, 2026-11-09):** one production Worker (`ains-platform`) and one API until pilot-ready. Existing preview/demo Workers are frozen; preview-first is paused. Lane C owns the new VPS; code agents have no server access. Source configuration does not prove deployment.
- **Mock gap:** many screen contracts still use the typed mock layer and browser storage, including firm settings. Production must not fall back to mocks. Lane 2 builds backend contracts and Lane 1 wires them; see [frontend inventory](frontend-inventory.md) and [build plan](BUILD-PLAN.md).
- **Gates:** G1 requires every Stage 1 acceptance item with evidence; G2 requires the Stage 2 security audit and Abdullah's written sign-off; G3 starts the engine only after G2. Real client data additionally requires all 45 readiness items and Abdullah's written authorization.
- **Deployments:** none were made in this cleanup.

## Test results

Quoted exactly as PR #84 states them:

- Normal suite: **339 passed + 1 skipped**.
- PostgreSQL 16.15: **11 tests run** on real PostgreSQL. These are not part of the normal suite.
- **CI now has a PostgreSQL 16 service** (`.github/workflows/ci.yml`, throwaway CI-only credentials, `KIEN_TEST_POSTGRES_URL`). The 11 PostgreSQL tests run on every pull request, each on a fresh database, and a CI step fails if any of them is skipped. Counts from the first CI run are recorded in the PR that added this.

Other runs recorded in the evidence files use different counts, for example 350 passed + 1 skipped on b6de342 in [checkpoint-TEST-4](evidence/testing/checkpoint-TEST-4.md). Those runs were on other candidates. Do not mix the counts. Quote the #84 numbers unless a run is re-done and recorded.

The raw PostgreSQL console output was not kept in the sandbox. What remains is the summary in the checkpoint files, linked below. The drill results are the raw per-check TSV files.

## Backup restore drill

The drill ran 27 checks on several candidate commits. Results are in the TSV files:

- [drill-results-b6de342.tsv](evidence/testing/drill-results-b6de342.tsv): 27/27 PASS as shipped. This is the final result.
- [drill-results-89d925f.tsv](evidence/testing/drill-results-89d925f.tsv) and [drill-results-89d925f-with-D9-patch.tsv](evidence/testing/drill-results-89d925f-with-D9-patch.tsv): earlier runs.
- [drill-results-b2cd6ae.tsv](evidence/testing/drill-results-b2cd6ae.tsv): first run, 26 PASS and 1 FAIL (defect D1, since fixed).

The drill used a software S3 stand-in (moto), not real R2, and a `docker` stand-in. It is emulator coverage only. Not run: real R2, object-lock drill, Docker build, Caddy, systemd, ClamAV, OpenRouter.

## Evidence in this repo

- [docs/evidence/testing/](evidence/testing/): drill TSVs, checkpoint notes TEST-1 to TEST-4, verify reports 1, 2, 4, 5, 6, 7.
- [docs/evidence/research/public-aml-test-data-sources.md](evidence/research/public-aml-test-data-sources.md): AML test-data research. Nothing was built or scraped from it.
- [docs/readiness/readiness-checklist-2026-11-07.md](readiness/readiness-checklist-2026-11-07.md): the 45-item readiness checklist.
- Not committed on purpose: the `handoff/*.bundle` files, the planning documents in `plans/`, and scratch probe and patch files. They stay in the project files.

## Open pull requests (triage, 2026-11-09)

Ten PRs were open. Actions taken or proposed:

| PR | Title | Decision | Reason |
| --- | --- | --- | --- |
| #1 | Client progress and auditor review frontend | Keep | 23 commits and no merge base with `main`; built on an October 21 branch. Review against the current frontend before any rebuild. |
| #37 | Configure portal API URL | Keep | Most of it is on `main` (credentials, env-driven CORS, production build script). Still open: production API URL default and Wrangler production vars. Rebuild on `main` first. |
| #39 | Synthetic Postgres backup restore drill | Close as superseded | `main` already has the restore drill (`deploy/backup/restore-drill.sh`, from b6de342), with 27/27 results above. |
| #40 | Resend mail for reset and report-ready | Keep | Invitations already send via Resend on `main`. Password reset and report-ready mail exist only here. Needs a rebuild on `main`. |
| #41 | Public landing page | Keep | Not on `main`. Public site: needs Abdullah's review before any deploy. No DNS touched. |
| #45 | Firm portals on slug subdomains | Keep | Tenant branding and slug hosts are not on `main`. The rebuild changes Terraform and DNS, which are on hold with the VPS. |
| #50 | Apple-style polish (draft) | Keep, decision needed | Ochre active pill and extra ochre accents conflict with the approved neutral look in `DESIGN.md`. Abdullah to decide: likely close. |
| #62 | Design skills and a11y tooling | Keep | Playwright and axe a11y config is not on `main`. About 210 third-party skill files need review first. |
| #63 | Maroon accent palette (preview only) | Keep, decision needed | Conflicts with the approved neutral look. Design experiments go on a separate address (rule 7). Abdullah to decide: likely close. |
| #73 | Page titles, 404 page, no em dashes | Keep | 404 page and titles are not on `main`. Needs a rebase on `main`. |

Only #39 was closed. Rebuilds were not started: #40, #45 and #37 each need their own branch and PR, and the coordinator asked that rebuilt PRs be listed rather than merged.

## Open decisions for Abdullah

1. Whether #50 and #63 are closed.
2. Whether #40, #45 and #37 are rebuilt on `main` now, or after the VPS phase resumes.
3. The partner-firm conflict in [VISION.md](VISION.md) needs legal and commercial advice before any decision.
4. The items in the readiness checklist marked for Abdullah, starting with Phase 0.

## Lane 2 checkpoint (2026-11-09)

- L2-1: #37 rebuilt on current main and merged in [#92](https://github.com/abdullah-kynetic/ains-platform/pull/92) (`74f1759`); original #37 closed as superseded. CI backend and web (including full browser tests) passed; independent source, tests and production artifact review PASS. Local backend: 369 passed, 11 skipped; web unit: 28 passed; lint/typecheck, demo and production builds passed. Production browser artifact contains `https://api.kiensolutions.com`. No deployment.
- L2-0: [#90](https://github.com/abdullah-kynetic/ains-platform/pull/90) merged after #92. Independent review confirmed the CI step "Postgres tests must run, not skip" passed. The older no-Postgres CI statement above is historical; current main includes the service.
- L2-2: [#93](https://github.com/abdullah-kynetic/ains-platform/pull/93) merged (`c40415a`), report-ready rebuild; original #40 closed. Ordered migration/email/reset/report regression: 31 passed; independent verify PASS. Full fixed backend: 377 passed, 12 skipped locally; both CI jobs, including PostgreSQL and browser tests, passed.
- L2-3: [#96](https://github.com/abdullah-kynetic/ains-platform/pull/96) open, portal rebuild. Post-fix focused suite: 106 passed, 1 PostgreSQL test skipped locally (no binaries). Independent security source review PASS; full pre-integration backend: 398 passed, 13 skipped locally. Integrated report-ready links passed the 50-test focused suite. Integrated backend at candidate `5603d78`: 409 passed, 12 skipped locally. A later ownership correction in #96 restores Lane 1's migration-head test, which still expects a117 and needs Lane 1's a119 update; that candidate requires a fresh full gate. Candidate PostgreSQL CI passed; live browser gate is blocked below.

### Requests to Lane 1

#92 landed the #37 package/Wrangler changes; Lane 1 now owns those files. Preserve the build-time API URL helper and its tests when updating production build guards. No dependency change requested.

BLOCKED(Lane 1): #96 live browser tests use `http://kynetic.localhost:3100`, but `scripts/e2e_backend.py` seeds only firm slug `synthetic-e2e`. With portal binding enabled the branding request returns 404 `Unknown firm portal`; client sign-in fails. Full candidate live run: 2 passed, 6 failed. Align the seed slug with the test hostname (or update the live test hostname and hard-coded URL assertions together). Lane 2 does not own `scripts/e2e_backend.py` or Playwright specs/config. Do not weaken host binding to make this fixture pass.

BLOCKED(runtime): local full mock browser run: 80 passed, 2 failed. Both production-style mapped aliases receive `Domain forbidden` from the managed proxy; a targeted retry with local-alias proxy bypass also failed. CI's full #92 browser step passed. Browser dependency install required unavailable root access; bundled download was forbidden; installed Chromium successfully ran the other 80 tests.

### BLOCKED inputs

BLOCKED(owner/attorney): reconcile readiness item 41 with CLAUDE.md rule 10; no real client data or model work is authorized by this checkpoint.
BLOCKED(Lane C): live R2/ClamAV, email delivery, host configuration and server evidence require the server lane; code agents have no server access.
## Lane 2: report-ready rebuild

DECISION: Rebuilt #40 on current main. Password-reset delivery already exists on main and is covered by `tests/test_password_reset.py`. Reverted the branch's `migrations/env.py` logging change: report notification delivery does not need to change Alembic's global logger configuration. Omitted the README change to preserve lane ownership; behavior is recorded here instead. Only active clients of the signed engagement's firm receive the generic report-ready notice. Mail exceptions do not undo sign-off; exception messages, addresses, keys and report content are not logged.


### Remaining plan work

L2-5 security proof suite, L2-6 route groups (a)–(h), L2-7 storage retention/export,
L2-8 remaining end-to-end flows, L2-9 seed hooks, and L2-10 readiness tracker are not
completed by this checkpoint. Existing tests are not a substitute for their required
evidence. No server changes, real email delivery or Stage 1 gate completion is claimed.

## L2-5 auth proof tranche

S-01 through S-06 now have executable proofs in `tests/security/` and evidence under `docs/security/evidence/app-s-*.md`. Focused suite: 15 passed; broader auth/reset/API: 70 passed. The initial full run found one legacy N/A assignment test retaining a token after its auditor changed firms; it now asserts revocation and signs in again before checking assignment. Final full gate and independent review pending. Existing sessions without role/firm claims must sign in again after deployment. No deployment was performed. S-07 through S-15 and S-19 remain in progress; no complete L2-5 claim yet.

## Lane 1: L1-7 wiring (2026-11-10)

The next web slices use main's assigned-auditor workspace for document receipt
metadata, its server activity feed (latest 20 events across assigned engagements),
and its existing six-stage pipeline. Receipt metadata is not upload/storage proof,
and receiving a document is not an auditor approval. Deploy code and DNS are
being handled separately; Lane 1 is skipping L1-3 and does not edit deploy or
compose files in this phase.

### Requests to Lane 2

The following contracts are missing from main at `9a8a10a`; the web must show an
unavailable/error state rather than synthesize successful writes. Existing types
in `web/src/lib/api/types.ts` remain the contract for the listed route groups.

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

No live proof of these missing behaviors is claimed. A backend route must enforce
firm ownership, assignment, role and workflow transitions; UI state is not authorization.

## Portal rebuild recheck after Lane 1 fixes

RESOLVED: #98 aligned the live fixture hostname with its synthetic firm and made the migration-head guard check the current single head. #96 merged current main, including #97 Security and #99 auth proofs. Its prior pre-auth full run passed 478 tests (12 skipped locally), and the corrected real local backend browser run passed all 8 tests. Fresh combined full CI, Security and independent verification are required before #96 merges. The auth/portal merge preserves request-time identity/MFA checks and portal firm binding; authenticated sign-out remains possible from any portal.

## Emailed sign-in codes replace TOTP (2026-11-11, branch claude/project-thread-v5w3qb)

After email + password, staff and clients get a 6-digit code by email (10 minutes, single use, 5 guesses,
resend and send limits). A correct code can remember the browser for 30 days (httpOnly cookie bound to
user and firm). Users can sign out other devices; partners/admins can revoke a team member's or an
assigned client's remembered devices. Audit: code sent, accepted, failed, device remembered, device
revoked. No Resend key (or `EMAIL_SIGN_IN_CODES=false`): password only, with a warning logged on every
sign-in. TOTP endpoints, recovery codes and the auditor-MFA session check are removed; the old columns
and table stay (additive migrations only). Migration `a129_email_sign_in_codes`. Demo seeds no longer
enrol TOTP. Tests: `tests/security/test_email_codes.py`. Env names: `docs/demo/DEPLOY-DEMO.md`.

## Lane 2 continuation checkpoint

L2-3 complete: #96 merged as `9a8a10a`; original #45 closed. Final combined backend: 493 passed, 12 skipped locally. Both local browser suites passed (82 mock, 8 real local API), including production-style aliases through a loopback-only test transport. Hosted CI/PostgreSQL, all nine Security jobs and independent security review passed. No server or deployment action occurred.

L2-5 next tranche: S-07/S-08/S-09/S-10/S-11/S-13/S-14/S-15 have security-suite modules and per-control evidence; 53 security tests passed. Full gate/review pending. S-12 log privacy and S-19 authorized download are separate follow-ups. S-16 depends on Lane 1's #100 database roles; S-17 headers belong to Lane 1/Lane C; S-18 live encrypted/object-locked backup restore evidence belongs to Lane C. These operational controls are not marked Done.

## Lane 2 workflow routes (2026-11-10)

Built in the workflow PR: checklist dispatch, reasoned N/A with auditor decision, stable
document numbers, client item links and submit, per-document issue flags with request threads,
per-item and engagement progress, client report confirmation, the invoice gate and the derived
stage pipeline. Contract: [`docs/kb/23-workflow-api.md`](kb/23-workflow-api.md). Requests to Lane 2
rows for these flows are satisfied once the PR is merged; no live proof is claimed. Direct client
N/A (`POST /engagements/{id}/items/{id}/na` with true) now returns 409; Lane 1 must move the
client UI to `na-request`.

## L2-6a practice routes (branch claude/project-thread-grvxp5)

Team, branding, rubric and request templates under `/auditor/firm/*`, per-practice scope, partner
guards and audit chain. Contract: [`docs/kb/24-practice-api.md`](kb/24-practice-api.md). Invites
create inactive members and send no email; logo upload waits for L2-7. No live proof is claimed.

## L2-6b checklist test conclusions (branch claude/project-thread-grvxp5)

`GET/PATCH /auditor/engagements/{id}/checklist-tests[/{requestId}]` store the auditor's own
pass, partial, fail or na per request (audit-logged, auditor-only). No conclusion is derived or
suggested. Documents are served by the existing live workspace route. No live proof is claimed.

## L2-6c workpapers and samples (branch lane2/l2-6c-workpapers-samples)

Workpaper save and independent review (preparer cannot review; edits clear review) and sample sets
with per-item results, auditor-only. Contract: [`docs/kb/25-workpapers-samples-api.md`](kb/25-workpapers-samples-api.md).
No live proof is claimed.

## L2-6d findings and response requests (branch claude/project-thread-grvxp5)

Auditor-only findings with server-enforced status moves and citation checks, explicit release of a
client response request, and the client's single reply. Clients see only the released title and
text. Contract: [`docs/kb/26-findings-api.md`](kb/26-findings-api.md). No live proof is claimed.

## L2-6e report draft (branch lane2/l2-6e-report-draft)

Server-assembled report draft from the auditor's own conclusions, samples and non-draft findings,
section edits, and real Word and PDF downloads, auditor-only. Contract:
[`docs/kb/27-report-draft-api.md`](kb/27-report-draft-api.md). No live proof is claimed.

## L2-6f independence and sign-off (branch lane2/l2-6f-signoff)

Independence declaration, second-reviewer approval, partner signature, completion and the client's
signed report are real routes (`app/api/signoff.py`, migration `a126_engagement_signoffs`,
contract `docs/kb/28-signoff-api.md`). Every step is a recorded human action and is audit-logged.
The legacy `POST /auditor/engagements/{id}/report/signoff` is untouched and still sends the
"report ready" email; the new flow sends no email.

## L2-6g activity, notifications, search (branch lane2/l2-6g-activity)

`GET /auditor/engagements/{id}/activity`, `GET /auditor/notifications` (+ read, read-all) and
`GET /auditor/search` are real (`app/api/feed.py`, migration `a127_notification_reads`, contract
`docs/kb/29-feed-api.md`). All are scoped to assigned engagements; none returns entered text.

## L2-6h client invoices (branch lane2/l2-6h-client-invoices)

`GET /engagements/{id}/invoices` gives the client their firm's sent and paid invoices
(`app/api/client_invoices.py`, contract `docs/kb/30-client-invoices-api.md`). Overdue unpaid
invoices also appear as auditor notifications. This completes L2-6 (groups a to h).

## L2-8 flows (branch lane2/l2-8-signed-report-confirm)

The client can confirm the signed report by fingerprint, which unlocks invoicing for engagements
that use the new sign-off path. `tests/test_end_to_end_flow.py` walks the whole journey. See
`docs/kb/32-report-confirmation-and-journey.md`. Live email and DNS are not verified here.

## L2-9 pilot seed and e2e seed (branch lane2/l2-9-pilot-seed)

`python -m app.pilot_seed` creates three synthetic pilot firms, one auditor and engagements, and
emails new invitations only with `--send`. `scripts/e2e_seed.py` adds the `kynetic-flow` firm in four
known states for the e2e-live specs. See `docs/kb/33-pilot-seed.md`. Never run with real data.

## L2-7 storage, retention, export, erasure (branch lane2/l2-7-retention)

R2 uploads no longer crash on the missing `VersionId`. `python -m app.retention export|plan|erase`
exports one firm's client-visible data and erases stored files of engagements past the retention
window (default 2190 days is a placeholder for the attorney). See
`docs/kb/31-retention-export-erasure.md`. Checked against moto only; no live bucket.

## Readiness tracker (L2-10)

All 45 readiness items now have a status, evidence link and owner in [`readiness/STATUS.md`](readiness/STATUS.md): 3 Done, 13 Partial, 2 Blocked, 27 Open. Done means evidence was run; no live R2, ClamAV, email or VPS check is claimed.
