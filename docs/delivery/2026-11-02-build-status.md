# Kien build delivery — 2 Nov 2026

Completed Phase 1 and the first Phase 2 backend slice. The full six-phase request is **not complete**. No deployment, shared-server operation, production migration, merge, AI feature or paid service was performed.

## Review order

1. `fix/demo-e2e` — [PR #74](https://github.com/abdullah-kynetic/ains-platform/pull/74): explicit synthetic test roles, current routes/navigation, preserved privacy/accessibility/N/A checks, opt-in onboarding and legacy print fixes.
2. `docs/current-product-context` — [PR #75](https://github.com/abdullah-kynetic/ains-platform/pull/75), based on the first branch: Quentin spelling, merged source status, neutral design, current owner-supplied OVH versus planned AWS, mock/backend and removed-auth boundaries.
3. `feat/client-profiles`, based on the second branch: client profiles/contacts and engagement summaries; additive `a116_client_profiles`; role/firm/assignment checks; contact audit event; real frontend API calls outside `USE_MOCKS`.

Use real merge commits in this order. Abdullah reviews; nothing has been merged.

## Exact checks and results

Commands ran from the repository root unless marked `web/`. Cache overrides keep writes inside the permitted workspace.

| Command | Result |
| --- | --- |
| `npm ci` (`web/`) | Failed: default npm cache was read-only |
| `npm ci --cache /tmp/kien-npm-cache` (`web/`) | Passed; 660 packages installed |
| `uv sync --frozen` | Failed: default uv cache was read-only |
| `UV_CACHE_DIR=/tmp/kien-uv-cache uv sync --frozen` | Passed |
| `npm run lint` (`web/`) | Passed after renaming the Playwright fixture callback to avoid React's hook rule |
| `npm run typecheck` (`web/`) | Passed |
| `npm run test:unit` (`web/`) | 11 passed |
| `PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=/usr/bin/chromium npm run test:e2e -- --workers=2` (`web/`, cleanup commit) | Final complete run: 65 passed in 4.4 minutes |
| `PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=/usr/bin/chromium npm run test:e2e -- e2e/frontend-screens.spec.ts e2e/redesign.spec.ts --workers=2` (`web/`, client slice) | 11 passed |
| `UV_CACHE_DIR=/tmp/kien-uv-cache uv run ruff check .` | Passed |
| `UV_CACHE_DIR=/tmp/kien-uv-cache uv run pytest tests/test_workflow_boundary.py -q` | 1 passed |
| `UV_CACHE_DIR=/tmp/kien-uv-cache uv run pytest tests/test_client_profiles.py tests/test_workflow_boundary.py -q` | 6 passed |
| `UV_CACHE_DIR=/tmp/kien-uv-cache uv run pytest tests/test_client_profiles.py -q` | 5 passed after response-contract/type refinements |
| `UV_CACHE_DIR=/tmp/kien-uv-cache uv run pytest tests/test_backend_api.py tests/test_client_profiles.py tests/test_workflow_boundary.py -q` | 51 passed |
| `UV_CACHE_DIR=/tmp/kien-uv-cache uv run pytest tests/test_client_profiles_postgres.py -q`, with `KIEN_TEST_POSTGRES_URL` set to the isolated local PostgreSQL 16 container | 1 passed: additive upgrade, metadata parity, downgrade, existing synthetic firm preserved, re-upgrade |
| `UV_CACHE_DIR=/tmp/kien-uv-cache uv run pytest tests/test_deployment_migration.py tests/test_client_profiles.py tests/test_workflow_boundary.py -q` | 7 passed after updating the expected single migration head |
| `UV_CACHE_DIR=/tmp/kien-uv-cache uv run pytest -q` | First run: 219 passed, 5 skipped, 1 failed because the expected head still named a115. Final run after correction: **220 passed, 5 skipped**, one Starlette/httpx deprecation warning |
| `NEXT_PUBLIC_USE_MOCKS=true npm run build` (`web/`, stacked client changes) | Passed |
| `WRANGLER_SEND_METRICS=false WRANGLER_LOG_PATH=/tmp/kien-wrangler.log npm run build:cloudflare` (`web/`, stacked client changes) | Passed; build only |
| `git diff --check` | Passed |
| `UV_CACHE_DIR=/tmp/kien-uv-cache uv run python -` (cleanup documentation probe) | Confirmed source head a115 at that slice; 0 missing local Markdown targets |

Earlier browser diagnostic runs found stale selectors, removed auth controls and onboarding/printing regressions. All 65 tests remain; none are skipped or deleted. The combined workspace journey no longer exercises deliberately removed MFA/password-acceptance UI; restore those assertions with auth in Phase 3. The questionnaire check now verifies that a real auditor request picker exists and excludes N/A, avoiding a vacuous assertion against the removed client picker.

## Screenshots

Before/after desktop light, desktop dark and phone captures for onboarding and invoice printing are committed in [evidence/demo-e2e](../evidence/demo-e2e). Documentation and client API wiring introduce no layout changes.

## Limits and decisions

- The default suite's five PostgreSQL skips remain skips; only the new profile migration was separately verified on PostgreSQL 16. Other skipped PostgreSQL coverage was not run.
- Browser results are synthetic and include routed API fixtures, not proof of live authentication, email, storage or deployment. Current deployed versions and bindings were not inspected.
- Client business metadata editing and reviewer/partner assignments are not implemented in this slice. Missing values remain empty. `signedOn` is null until verified signature evidence is wired; `onboardedOn` is firm-record creation, not proof of invitation acceptance.
- Decisions needed: Stripe entity/account/methods and fees; AWS target/budget; backup RPO/RTO and retention; security owner; auditor hostname/access policy. Preserve existing client undo-N/A behavior pending the owner's decision.
- Needs Quentin: rubric, allowed evidence, severity, report and sign-off wording. Needs attorney: privacy/terms and regulatory contract wording. No audit/legal criteria were invented.

## Remaining scope

| Phase | Status |
| --- | --- |
| 1 — cleanup | Complete in PRs #74 and #75; awaiting review |
| 2 — new screen backend | Clients/contacts/summaries implemented; checklist/documents through client results remain |
| 3 — restore auth | Not started; required before any live deployment or real data |
| 4 — security hardening | Not started |
| 5 — follow-ups / test-mode Stripe | Not started; account decisions pending |
| 6 — AWS preparation | Not started; infrastructure must not be applied |

Next authorized slice: Phase 2.2 checklist conclusions and document listing, with additive schema, assignment/firm filtering, audit entries, real API clients and cross-tenant denial tests.
