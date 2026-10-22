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

Phases 3 through 8 will be reviewed and appended here in order. Each phase is merged only after
its own PR checks pass, using a merge commit. Later unmerged feature branches are not silently
included in this consolidation. Their useful work can be incorporated into the subsequent tasks.
