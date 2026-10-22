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

## Review sequence

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

Phases 6 through 8 will be reviewed and appended here in order. Each phase is merged only after
its own PR checks pass, using a merge commit. Later unmerged feature branches are not silently
included in this consolidation. Their useful work can be incorporated into the subsequent tasks.
