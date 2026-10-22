# Branch consolidation review

This application manages audit workflow only. Model inference belongs in a separate pipeline;
future integration must use an authenticated backend adapter. Use synthetic data only. Do not
add real client documents, restricted-content fixtures, or hardcoded credentials.

## Already in main

- `codex/portal-review` (`7f56024`): restored the portal's ignored library files and working
  synthetic client overview/checklist. This was already merged before consolidation.
- `codex/phase-0-ci` (`200e022`): Python lint/tests and web lint/typecheck/build CI. Already in main;
  opening empty replacement PRs would not add code or improve history.

## Phase 2 — backend foundation

Delivered SQLAlchemy/Alembic models, tenant-scoped engagement and document endpoints,
password/magic-link sessions, auditor MFA checks, CORS, and cross-tenant denial tests.
Storage is an injectable boundary and intentionally returns unavailable until phase 4.

Unfinished: invitation/first-auditor setup, MFA enrollment and recovery, email delivery,
production session/cookie configuration, login throttling, and administrative UI. Magic-link
delivery currently uses an unconfigured no-op adapter and must not be enabled for production.
There are no model calls in this phase. Models for findings/check results are data containers.

## Phase 3 — questionnaire

Delivered conditional yes/no questions, client answers, pending/approved/rejected N/A review,
and auditor-scoped decisions with audit logging. Cross-tenant and client-role denial tests exist.
Unfinished: no free-text representation collection; negative answers hide requests before auditor
approval, and changed answers can reset a previous review. Task 4 must preserve required
representations and distinguish proposed applicability from approved applicability. No model calls.

## Phase 4 — guarded storage uploads

Delivered filename/size/signature validation, SHA-256 fingerprints, per-item accepted extensions,
guarded firm/engagement/request folders, and raw-body Egnyte uploads with SHA-512 transport
checksums. Tests mock storage; no real documents or credentials are needed.
Unfinished: live account verification, stronger Office-container validation, central upload UI,
file-level receipt/error handling, and rejecting inactive/hidden requests. Task 3 addresses the
upload flow; antivirus/quarantine and production storage policy remain deployment work.
No model calls are present.

## Phase 5 — durable storage receipts (model code removed)

The original branch included direct Anthropic/OpenAI HTTP calls, automatic sufficiency mapping,
document extraction, and synthetic restricted-content fixtures. These are removed before merge,
along with model credentials/configuration and provider-specific tests and dependencies.
The retained worker verifies stored SHA-256 fingerprints, records receipt/timing, retries failed
jobs, and routes files to the auditor. It cannot create findings or decide evidence sufficiency.
Unfinished: worker operational monitoring, stale-version policy, and a future authenticated
external-pipeline adapter. Direct inference is deliberately out of scope, not a pending feature.

## Phase 6 — auditor review and unsigned drafts

Delivered assigned-auditor evidence queues, manual finding accept/edit/reject actions, severity,
citations, audit records, and swappable DOCX/PDF draft-report templates. The citation data model
is moved to a neutral evidence module; no dependency on removed model providers remains.
Merge conflicts in tests/dependencies preserve the receipt-verification tests and add only report
libraries. Unfinished: complete request-level decisions/history, document download/viewing,
report-readiness gates, citation source naming, and final signing/delivery. Task 5 owns these gaps.

## Phase 7 — portal API wiring

Delivered backend-owned sign-in/session UI, client questionnaire, uploads, auditor evidence and
finding review pages, report downloads, and PATCH CORS support. Fixed the finding-state contract
from the nonexistent `draft` enum value to the backend's `pending` value.
Unfinished: the demo's handwritten request data, central upload flow, onboarding/admin screens,
stronger loading/error/empty states, and document/request-level manual review. Tasks 2–6 replace
these progressively. Magic-link delivery remains unconfigured; live deployment is not implied.
No model calls are introduced by this frontend phase.

## Phase 8 — synthetic upload validation (provider evals removed)

Retained six synthetic upload cases and an offline validation command. Removed the model-based
evaluation runner, provider flags, automated audit-status scoring, and restricted-content fixture.
Added a regression check against reintroducing direct model endpoints, SDK imports, or settings.
Wrong-period and partial documents are received, not automatically judged by the application.

## Consolidation outcome

Phases 2–8 are consolidated through separate PRs and merge commits, with CI required before
each merge. Phase 0 and the portal repair were already ancestors of main. Later feature branches
remain unmerged because they contain superseded model-related code and duplicate catalogs;
their useful workflow/UI work must be adapted in Tasks 2–6, not merged wholesale.

This is a reviewed foundation, not a finished app. The canonical 34-item catalog with empty
auditor rubrics is Task 2; central uploads Task 3; representations/client flows Task 4; full
manual request decisions/history/readiness Task 5; complete screen polish/accessibility Task 6.
Live storage, identity provisioning/email/MFA recovery, hosting, and operational hardening remain
deployment prerequisites. No real client data or model inference is needed for the requested demos.
