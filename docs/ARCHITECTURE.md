# Architecture

> **Web sign-in status:** web sign-in is restored and calls the secured backend (password, auditor MFA, invitations, password reset, lockout messages, sign-out). The synthetic demo (`NEXT_PUBLIC_USE_MOCKS=true`) still opens as a demo user without sign-in. Verified by `web/e2e-live` against a local backend with synthetic users; not deployed. Backend enforces authentication, MFA, firm isolation and assignment. Screens and mocked calls are listed in [frontend-inventory.md](frontend-inventory.md).

## System purpose

Kien supports evidence collection and independent human AML testing for broker-dealers under FINRA Rule 3310. The browser provides client and auditor workflows; FastAPI authenticates requests, applies role/firm/assignment rules, validates upload metadata, and coordinates PostgreSQL and object storage. Database-backed workflow checks verify storage receipts, not document contents or audit conclusions. No model inference is in `app/`.

## Stack decisions

| Layer | Selected technology | Reason | Constraints |
| --- | --- | --- | --- |
| Frontend | Next.js 16 App Router, React 19, TypeScript, Tailwind v4 | Responsive client/auditor workflow and Cloudflare build | Browser requests FastAPI; mocks are synthetic only; public `NEXT_PUBLIC_*` values are not secrets |
| Backend/API | Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2 | Central authentication, validation, and workflow boundary | All authorization is server-side; no model SDKs/calls |
| Database | PostgreSQL 16, SQLAlchemy models, Alembic migrations | Relational tenant/workflow state and durable queue | FastAPI owns access; no direct browser DB access |
| Authentication | App-owned password/invitation/session flow, auditor TOTP MFA and hashed recovery codes | Roles, firm binding, assignment and step-up are app-enforced | Session cookie and secret configured server-side; client accounts are invite-only |
| Hosting | Owner-supplied runtime: Cloudflare Worker frontend + OVH Docker/Caddy API; repository also contains AWS single-host Terraform/deployment docs | Runtime is stated by the owner; repo provides an alternative deployment path | OVH is the owner-supplied current backend target; AWS is planned. Runtime was not inspected. |
| Object storage | Owner-supplied Cloudflare R2 bucket `kien-dev-documents`; code supports S3 API, default `STORAGE_BACKEND=s3`, optional Egnyte | Store uploaded documents outside relational DB | Bucket/location/current production configuration are not verified in repo. Egnyte is optional/off by default. |
| Email | Resend sender in `app/auth/email.py`; owner supplies no-reply/invite sender addresses | Invitation and recovery delivery | Variable names only: `RESEND_API_KEY`, `EMAIL_FROM`, `INVITE_EMAIL_FROM`; code has no addresses hard-coded. |

Runtime/domain assertions supplied by the owner: `live.kiensolutions.com` Worker `kien-demo-live`, `api.kiensolutions.com`, preview/design Workers, OVH Docker + Caddy, Postgres 16, R2 bucket `kien-dev-documents`, and Resend senders `no-reply@kiensolutions.com` and `invite@kiensolutions.com`. The checked-in source supports Worker configuration/build, FastAPI, PostgreSQL, S3-compatible storage, and Resend integration, but does not establish those live resource names or values; treat them as owner-supplied deployment facts pending verification. `NEXT_PUBLIC_USE_MOCKS` makes the demo run with synthetic mock data; mock mode is not real authentication or persistence.

## System boundaries

- **Client owns:** rendering and input interaction, client-side validation for usability, selecting files, and displaying only data returned by API. Browser code cannot grant role access. `NEXT_PUBLIC_API_URL` is public build-time configuration; `NEXT_PUBLIC_USE_MOCKS` enables synthetic preview behavior.
- **Server owns:** session validation; role, firm, and auditor assignment authorization; input validation; business rules; upload validation/hash/receipt; writes to SQL and configured storage; audit-chain append; report draft and sign-off action.
- **External services own:** Cloudflare edge/runtime (if deployed there), PostgreSQL persistence, S3-compatible R2 or optional Egnyte document bytes, Resend delivery, and Sentry telemetry when configured. Failures must be surfaced without exposing secrets or document contents.
- **Out of scope:** model inference, sending SAR material to a model, browser-to-database access, public signup, and any deployment or migration without explicit task authorization.

## Request and data flow

1. A client opens the firm portal; the host/tenant helper resolves firm branding and the session context. Client UI shows only its bound firm and neutral checklist status.
2. The client selects one or more files via drag/drop or picker, confirms, and the browser posts multipart content to the FastAPI endpoint using the session cookie. Client does not select a checklist destination at upload time.
3. FastAPI validates user/session, active firm/engagement ownership, file size/type/name constraints, hashes the bytes, stores the object using configured `StorageBackend`, and persists firm/document metadata. The storage key is firm-scoped; SQL metadata records the storage path/key, hash, version, uploader, size, and timestamp.
4. The API enqueues a Postgres-backed `CheckJob`. `app/worker.py` claims jobs and verifies stored receipt/integrity metadata; it does not inspect document content or invoke a model. Results and job state remain firm-scoped.
5. Auditor requests authenticate the auditor and check assignment to the engagement (and firm-level assignment where applicable), then read/write workflow records and append chained audit events in the transaction. Client responses omit internal notes and findings.
6. The browser renders a receipt or neutral status. Validation/service failures return an API error; UI shows a per-file error, retry, or sign-in recovery path. Upload receipt is not evidence acceptance or a finding.
7. An assigned auditor may generate a report draft and explicitly sign off by providing the draft hash and attestation. API records the approved hash and completes the engagement; this is not a cryptographic PDF/DOCX signature.

## Interfaces

- **API contract:** FastAPI routers are mounted from `app/main.py`; route families include `/auth`, `/tenant/branding`, client engagement/questionnaire/intake/upload routes, `/auditor` engagement/task/review/audit-log routes, and health/monitoring. JSON schemas use Pydantic; uploads use multipart form data. Errors use FastAPI `HTTPException` status/detail responses. Inspect route modules for exact request/response schemas; this document does not freeze every endpoint.
- **Browser API:** `web/src/lib/api.ts`, `workflow-api.ts`, and `audit-api.ts`; base URL from `NEXT_PUBLIC_API_URL`; mock mode controlled by `NEXT_PUBLIC_USE_MOCKS`.
- **Jobs:** API creates unique per-document `check_jobs`; Postgres row state provides queued/running/succeeded/failed, attempts, availability and duration; `app/worker.py` processes receipt checks. Retry policy/stale job operations are not fully documented; operational controls remain unresolved.
- **Audit events:** `app/audit.py` creates per-firm SHA-256 chained events; authentication events without a firm use system chain. Postgres trigger and ORM guards reject mutation. This provides tamper evidence against ordinary updates; privileged database rewrite remains possible.
- **Storage:** `app/storage/s3.py` supports configured S3-compatible storage. `app/egnyte_client/` is an optional guarded Egnyte client; development access is limited to `/Shared/AINS-Dev` through its client/CLI.

## Project structure

| Path | Responsibility |
| --- | --- |
| `app/main.py` | FastAPI app construction, router mounting, middleware, health |
| `app/config.py` | Environment-backed settings; secret/config access |
| `app/auth/` | Password/session, invite/reset/magic link, auditor MFA, email |
| `app/api/` | Client and auditor HTTP route handlers |
| `app/database/` | SQLAlchemy models and session/engine lifecycle |
| `app/documents/` | Upload validation, hashing, storage ingestion |
| `app/storage/` | Storage abstractions and S3-compatible backend |
| `app/checklist/`, `data/checklist/` | Checklist schema/catalog and 34 stable request IDs |
| `app/checks/`, `app/worker.py` | Receipt checks and Postgres-backed background queue |
| `app/audit.py`, `app/evidence.py` | Audit-chain and evidence/workflow helpers |
| `app/reports/`, `templates/report/` | Human-review report draft generation and templates |
| `app/egnyte_client/` | Optional Egnyte API client, path guard, rate limiter, CLI |
| `migrations/` | Alembic environment and versioned schema migrations |
| `tests/` | Backend unit/integration tests, synthetic fixtures |
| `web/src/app/` | Next.js routes, layouts, global styles |
| `web/src/components/ui/` | Shared UI primitives |
| `web/src/components/{shell,checklist,auditor,tenant,auth,brand}/` | Workflow and application components |
| `web/src/lib/` | API clients, mock data, tenant/checklist utilities |
| `web/e2e/`, `web/src/**/*.test.ts` | Playwright e2e and Node unit tests |
| `infra/aws/` | Planned AWS migration Terraform/bootstrap; not the current OVH runbook |
| `docs/` | Product, design, architecture, database, security, style, testing and operational notes |
| `.github/workflows/` | CI workflows |

## Operations

- **Environments/configuration:** Local backend uses `DATABASE_URL`, `STORAGE_BACKEND`, and related variables from `.env.example`; web uses `NEXT_PUBLIC_API_URL` and `NEXT_PUBLIC_USE_MOCKS` from `web/.env.example`. Never expose backend secrets through `NEXT_PUBLIC_*`. There is a synthetic web demo mode. OVH is current per the owner; AWS is planned. Exact deployed bindings remain unverified.
- **Deployment/rollback:** Repository includes Docker Compose for PostgreSQL/API/worker, Dockerfile, AWS Terraform, Caddy bootstrap, and Cloudflare Workers build config. Production deployment and rollback runbooks are incomplete; do not deploy from this doc.
- **Monitoring:** `app/monitoring.py`, health/metrics endpoints, optional Sentry configuration exist. Operational thresholds, alerts, backup/restore and queue recovery procedures are unresolved.
- **Scale limits:** Upload limit is 100 MB per file in current code/UI; Egnyte simple upload also caps at 100 MB. Worker uses the database queue. No approved throughput or retention SLO exists.

## Decisions and unknowns

- Confirm active runtime provider/host, domain and Worker names, object bucket/account, email sender addresses and environment bindings. Code verifies integrations, not deployed resource existence.
- Confirm storage retention and deletion, backup frequency/restore target, job retry/recovery, production monitoring, and cryptographic report signing expectations.
- AI intake and SAR pre-screen are planned only. Any future classification requires auditor confirmation; SAR data must never reach model inference.

## Invoicing boundary

`app/invoicing.py` owns exact financial arithmetic, numbering and transitions;
`app/api/invoices.py` exposes `/auditor/invoices` list/get/create/PATCH and POST
`/{id}/sent`, `/{id}/paid`, `/{id}/void`, plus assignment-scoped `/options`.
Filters are `status`, `client`, inclusive issue-date `since`/`until`, `limit` (max 200)
and `offset`. Web pages use `web/src/lib/invoice-api.ts`; mock mode persists synthetic
invoice metadata locally. Payment recording does not contact a payment or mail service.
The printable detail uses browser print/save as PDF. Invoice data is shared by the issuing auditor firm and requires a current matching
client/engagement assignment to an auditor in that firm. Unbound issuers stay private.


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


## Web portals by host

One web app on one Worker serves two audiences. Clients use `<firm>.kiensolutions.com`; auditors use one fixed host (`NEXT_PUBLIC_AUDITOR_HOST`); demo hosts serve both. `audienceForHost()` in `web/src/lib/audience.ts` narrows the UI only. The API must still enforce role and firm. Screens without a backend route call a typed mock layer (`web/src/lib/api/*`, `web/src/lib/mock/*`), documented in `frontend-inventory.md`.

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

## Client profile backend

`app/api/client_profiles.py` implements assigned-auditor profile/contact reads, contact creation and per-engagement summaries. The existing engagement register includes additive summary fields while preserving its dashboard contract. `web/src/lib/api/clients.ts` uses these routes outside `USE_MOCKS`. All other unimplemented new-screen contracts remain listed in the frontend inventory. No auth bypass or automatic finding/report approval is introduced.
