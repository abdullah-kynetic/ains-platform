# Code Style

## Languages and conventions

- **Language/version:** Python >=3.12; TypeScript/JavaScript for web (Next.js 16, React 19); CSS/Tailwind v4; SQL through SQLAlchemy/Alembic; Terraform for `infra/aws/`.
- **Naming:** Python modules/functions/variables snake_case; classes PascalCase; SQLAlchemy table names plural snake_case. React components/types PascalCase; component/module files generally kebab-case; hooks start `use`; TS variables/functions camelCase. Follow local pattern where existing files differ.
- **Formatting/linting:** Ruff configured in `pyproject.toml`: line length 100, target py312, rules E/F/I/B/UP. Web ESLint 9 via `web/eslint.config.mjs`; TypeScript strictness/options from `web/tsconfig.json`. No configured Python formatter command was found; Ruff lint is configured. No Prettier script is configured.
- **Type safety:** Use Python annotations and Pydantic models at HTTP boundaries; SQLAlchemy 2 typed mappings; TypeScript types for API/component data; do not weaken compiler settings or duplicate API types without need.

## Organization

Directory responsibilities are defined in [Architecture](ARCHITECTURE.md#project-structure). Key boundaries:

- Shared backend business rules belong in `app/` services/domain modules, not copied into route handlers. `app/api/` adapts HTTP; `app/auth/` handles identity/session; `app/database/` owns persistence mapping; `app/documents/` handles uploads; `app/worker.py` owns durable receipt jobs.
- Shared visual primitives belong in `web/src/components/ui/`; workflow modules stay in `components/checklist`, `components/auditor`, `components/tenant`, etc. API access belongs in `web/src/lib/` rather than ad-hoc fetch logic scattered in pages.
- Tests mirror backend behavior in `tests/`, and browser flows live in `web/e2e/`; synthetic fixtures only.
- Keep FastAPI as the only database boundary. Do not add model SDKs/calls to `app/`.

## Coding rules

- Keep functions focused; follow established repository patterns.
- Validate external inputs at the trust boundary and authorize every tenant-owned operation server-side.
- Handle loading, empty, error, and success states explicitly.
- Avoid silent failures and undocumented magic values.
- Reuse existing components before introducing new abstractions.
- Never include real client files, secrets, or SAR contents in examples/tests/logs. Keep client feedback document-focused and neutral.

## Errors and logging

- API uses FastAPI `HTTPException` status/detail responses and Pydantic validation errors. Browser helpers surface API errors to explicit UI load/error states; preserve retry where safe.
- Do not log passwords, session or invitation/reset tokens, MFA secrets/recovery codes, uploaded bytes/content, provider authorization material, or sensitive bodies. Follow [Security](SECURITY.md).

## Dependencies

- New packages should be necessary and fit the existing runtime; update the correct lockfile (`uv.lock`, `web/package-lock.json`) in the same change. No formal approval policy is documented; explain dependency and runtime impact in review.
- Keep exact dependency locks and CI inputs aligned. Do not install packages for documentation-only tasks.

## Review checklist

- Implementation matches approved PRD acceptance criteria; unresolved behavior is not silently treated as approved.
- Types, lint, and verified checks use actual project commands.
- No credentials, real client data, or unrelated files in the diff.
- Tests cover meaningful behavior, including authorization and cross-tenant denial for new endpoints.
- UI preserves accessibility, reduced motion, demo labeling, and owner-approved style; UI change screenshots are desktop light/dark and phone before/after.

## Verified commands

- **Format:** Not configured as a dedicated command.
- **Backend lint:** `uv run ruff check .` (Ruff configured in `pyproject.toml`; CI workflow also invokes Ruff).
- **Backend tests:** `uv run pytest -q`.
- **Web lint:** from `web/`, `npm run lint`.
- **Web type check:** from `web/`, `npm run typecheck`.
- **Web unit tests:** from `web/`, `npm run test:unit`.
- **Web Cloudflare build:** from `web/`, `npm run build:cloudflare`.
- **Web e2e:** from `web/`, `npm run test:e2e`.
- **Local database:** `docker compose up -d` (PostgreSQL 16).

Scripts are confirmed in `pyproject.toml`, `web/package.json`, and `.github/workflows/ci.yml`. A command being documented does not imply it was run in this session; session results are in [Testing](TESTING.md#results).

Invoice arithmetic uses Decimal quantities and integer cents, half-up per-line rounding,
and server-derived totals. Web live totals use integer hundredths; browser-supplied totals
and invoice numbers are not accepted as authoritative inputs. No new dependency is needed.


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
signature. Clients receive 403 and have no report navigation; unassigned auditors get 404.
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
