# Testing

> **Demo-phase status (frontend):** web sign-in and auth are removed so the product can be built and verified end to end on synthetic data. Every web visitor is a synthetic user; the role comes from the sidebar workspace switcher on demo hosts and from the hostname on real hosts (`web/src/lib/audience.ts`). **The backend still enforces authentication, MFA, firm isolation and assignment; none of that changed.** Restore the web side before any real data by turning off `AUTH_REMOVED` in `web/src/lib/api.ts` (search `TODO(auth)`). Screens and mocked calls are listed in [frontend-inventory.md](frontend-inventory.md).

## Goals and scope

Before release, validate PRD journeys F-01 through F-10, especially server-side role checks, firm isolation, assigned auditor access, upload safety, neutral client feedback, and human-only findings/sign-off. Planned F-11/F-12 are not implemented and must not be reported as covered. CI contains backend and web jobs; see `.github/workflows/ci.yml`.

## Test layers

- **Unit:** pytest backend rules/helpers; web Node tests for tenant host and hostname-to-audience mapping (the sign-in redirect utility went with web sign-in). Synthetic storage providers and fixtures are used.
- **Integration:** FastAPI API tests with test database/storage fixtures; auth/MFA, invitation, firm/engagement isolation, upload, worker, report, and audit-log behavior. Postgres-specific audit-chain coverage may depend on local PostgreSQL binaries and can skip where unavailable.
- **End-to-end:** Playwright browser journeys in `web/e2e/`, using the synthetic web mock mode and synthetic files. E2E is not proof of live backend, cloud storage, or email behavior.
- **Manual:** Review screenshots and actual keyboard/focus/motion behavior for UI changes. Full human accessibility review and contrast certification are not automated.

## Acceptance test matrix

| Feature/risk | Scenario | Expected result | Layer | Status |
| --- | --- | --- | --- | --- |
| F-01 | Client requests own current engagement | Own firm/allowed fields returned | Integration | Covered in source; this session not run |
| F-01 / Isolation | Client requests another firm’s engagement/document/questionnaire | Denied with no cross-firm data | Integration | Covered in source; this session not run |
| F-02 | Client answers applicability / no-activity question | Answer persists; N/A applies immediately and can be undone | Integration/e2e | Covered in source; this session not run |
| F-03 | Client uploads several files without choosing request | Files receive unassigned, firm-scoped receipts | Integration/e2e | Covered in source; this session not run |
| F-03 / Security | Restricted item, invalid type, zero byte or >100 MB upload | Rejected before storage; safe error | Integration | Invalid type/oversize/restricted covered; this session not run |
| F-04 | Auditor gives document-level replacement feedback | Client sees neutral message and can re-upload | Integration/e2e | Covered in source; this session not run |
| F-04 / Privacy | Client attempts finding/internal-note/audit-log route | Denied or omitted from response | Integration | Covered in source; this session not run |
| F-05 / Permissions | Auditor accesses assigned engagement | Data available | Integration/e2e | Covered in source; this session not run |
| F-05 / Isolation | Auditor accesses unassigned engagement | Denied even if UI route is opened directly | Integration | Covered in source; this session not run |
| F-06 | Auditor records manual decision and review history | Decision and actor history persisted | Integration | Covered in source; this session not run |
| F-07 | Auditor signs report with hash and attestation | Assigned auditor sign-off recorded; client/other auditor denied | Integration | Covered in source; this session not run |
| F-08 | Auditor MFA challenge/enrollment/recovery | Challenge required when enrolled; recovery code single-use | Integration/e2e | Covered in source; this session not run |
| F-09 | Invitation or magic/reset token replay/expiry | Expired/used token rejected; no session created | Integration | Covered in source; this session not run |
| F-10 | Phone nav, keyboard, reduced-motion, theme, load retry | Usable responsive state, focus return, motion preference honored | E2E/manual | Browser tests exist; this session not run |
| Workflow boundary | Search app/forbidden dependency locations for inference provider calls | No direct model provider in workflow app | pytest | Executed this session; see Results |
| F-11 / F-12 | AI intake or SAR pre-screen | No implementation or model behavior claimed | N/A | Planned; not run |

Source examples include `tests/test_backend_api.py`, `tests/test_audit_log.py`, `tests/test_document_ingestion.py`, `tests/test_auth_readiness.py`, `tests/test_workflow_boundary.py`, and web specs for upload, auditor, accessibility, tasks, questionnaire, report/audit log, and responsive sidebar. Source presence indicates test implementation only, not a passing result.

## Fixtures and environments

- **Synthetic users/data:** `tests/conftest.py`, synthetic provider fakes, `app/demo_seed.py`, `data/synthetic/`, generated checklist catalog, and browser mock data. Never use real client evidence or actual SAR records in tests.
- **External services:** Backend tests mock or fake storage/email/provider boundaries; browser tests use `NEXT_PUBLIC_USE_MOCKS=true`. They do not validate live R2/Egnyte, Resend delivery, Worker deployment, or OVH/AWS production configuration.
- **Reset/isolation:** Tests build isolated test state via fixtures; Postgres audit integration may use private temporary cluster support when local binaries exist. Exact persistent service reset and production-data isolation procedures remain unresolved.

## Verified commands

- Backend unit/integration: `uv run pytest -q`; targeted workflow boundary: `uv run pytest tests/test_workflow_boundary.py -q`.
- Backend lint: `uv run ruff check .`.
- Web unit: from `web/`, `npm run test:unit`.
- Web e2e: from `web/`, `npm run test:e2e` (Playwright; browser install in CI uses `npx playwright install --with-deps chromium`).
- Web lint/type/build: from `web/`, `npm run lint`, `npm run typecheck`, `npm run build:cloudflare`.

These commands are confirmed in project configuration/CI. Only commands listed under Results were executed this documentation session.

## Release criteria

Required: applicable CI jobs pass; new endpoints have permission-denial and firm-isolation coverage; upload and auth changes include failure cases; no real client data/secrets; docs/code agree on behavior. The product owner and auditor approve acceptance decisions. An automated pass does not certify regulatory compliance or security.

## Results

### This documentation session

- **Passed:** `uv run pytest tests/test_workflow_boundary.py -q` — 1 passed in 0.07s.
- **Failed:** None.
- **Not run:** Full backend suite, Ruff, web lint/type/unit/build/e2e, accessibility screenshots, production service checks, and all other commands. Documentation-only changes do not alter application code.

### Auditor invoice coverage

`tests/test_invoices.py` covers draft CRUD, totals/rounding, per-issuer numbering,
status/date/client filters, partial/full payments and transitions, invalid input,
assignment revocation, cross-firm and client denial, and idempotent synthetic seeding.
`tests/test_invoice_postgres.py` applies the additive migration to a populated old schema,
checks model parity and races eight invoice creations against one issuer. Browser tests
in `web/e2e/invoices.spec.ts` cover create/edit/send/pay persistence, filters/void, print,
phone overflow, accessibility and direct client-route denial. Live deployment evidence and
exact session command results are recorded in the delivery report.


## Numbered checklist N/A

All 34 catalog requests remain visible with their original numbers; N/A sorts last.
Clients can directly set/undo N/A on their own engagement; its assigned auditor can
also set/undo it. Questionnaire no answers and the legacy representation endpoint
now set N/A directly. Existing pending claims remain readable and reviewable for
compatibility. N/A counts as done; collection still excludes the two restricted items
(32 ordinary requests). Restricted-content handling and upload prohibitions remain.
Undo restores `na_previous_state` (revision `a113_checklist_na`). The existing
`na_approved_by_id` stores the marking actor for both roles; the related user supplies
`naMarkedByRole`. Each toggle records actor ID and role in the immutable audit chain.
No schema migration is needed. This collection declaration is not an audit finding.
Auditor workspace links come from server-authorized assignments rather than a disabled
synthetic client-role switch. Unassigned auditors and other firms remain denied.


## Editable auditor reports

The existing report template, approved finding drafts, legacy DOCX/PDF generator and
hash-attestation sign-off remain in place. `/auditor/reports` adds persisted editing
per assigned engagement in `engagement_reports` (additive `a114_engagement_reports`).
Firm/period/scope and 34 request statuses are snapshotted server-side on create/save.
Approved findings prefill the narrative; auditors enter per-item report findings.
Restricted items allow metadata only. The native rich-text editor accepts text paste;
the server keeps only formatting tags with no attributes, scripts, URLs or embedded content.
Version checks and row locks prevent lost updates. Finalization requires explicit human
attestation, freezes content and records its SHA-256. Audited reopening permits edits;
prior final hashes remain in the immutable audit chain. Final status does not complete
the engagement, deliver a report, establish a clean opinion or create a cryptographic
signature. Clients receive 403 from the auditor editor; unassigned auditors get 404. The separate client Report screen is a synthetic mock pending its backend slice.
Print view uses the invoice-style browser print/save PDF flow. The idempotent
`python -m app.report_seed` seeds one existing explicitly synthetic demo engagement.


## First sign-in walkthrough

`GET/POST /auth/onboarding` reads/finishes only the authenticated user's preference.
Nullable `users.onboarding_state` and `onboarding_finished_at` are added by
`a115_user_onboarding`; null means pending. Completed/skipped states are terminal
through the public endpoint and audited once. Each role has a three-step skippable
modal using the existing dialog, focus handling, tokens and reduced-motion behavior.
The app has auditor/client roles and no distinct firm-admin role; the auditor flow
explains the workspace management auditors already have permission to use.
`python -m app.onboarding_seed --reset-demo` resets only the two exact existing
synthetic demo identities, preserves credentials and records demo reset events.
Demo walkthroughs stay finished after verification; reset only for an explicit demo run.
`UserView` includes nullable `onboarding_state` in sign-in, invitation acceptance and
`GET /auth/session`. Both roles open the tour only for null state, with no extra GET
required. Completing, skipping, Close and Escape save through the same idempotent
POST; the session updates only after a successful save. Failed saves stay visible
with a retryable error. Live mode never uses localStorage for onboarding state.
New users start null; existing pending users are not backfilled. No new migration
is needed beyond `a115`. Static browser mocks have no sign-in;
set `kien-synthetic-onboarding-enabled=1` to exercise their local walkthrough state.

## Client profile coverage

`tests/test_client_profiles.py` checks exact contract fields, contact validation/audit metadata, preservation of dashboard fields, other-firm/client denials, same-firm unassigned history, and revoked assignments across all profile/contact/summary paths. `tests/test_client_profiles_postgres.py` checks additive upgrade, model parity, downgrade and re-upgrade while preserving a pre-existing synthetic firm. The latter can use an explicitly configured isolated database via `KIEN_TEST_POSTGRES_URL`; without it, the existing temporary-Postgres fixture requires local binaries. Never point this test at a shared or production database.
