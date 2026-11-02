# SOP — Testing and QA

> **Source status (2 Nov 2026):** PRs #53–#60 and #64–#72 are merged in the checked-out history through `d822ce1`. The schema head is `a115_user_onboarding`. Merged source does not establish what is deployed. Runtime state was not inspected. Web sign-in is removed for the synthetic demo; backend auth, MFA and tenant isolation remain required. New screen contracts still use mocks; see [frontend inventory](../frontend-inventory.md).

## Commands (verified in CI config)
Backend (repo root): `uv sync --frozen` · `uv run ruff check .` · `uv run pytest -q` · targeted: `uv run pytest tests/test_workflow_boundary.py -q` · `uv run python scripts/evaluate_synthetic.py`
Web (`web/`): `npm ci` · `npm run lint` · `npm run typecheck` · `npm run test:unit` · `npm run build:cloudflare` · `npx playwright install --with-deps chromium` · `npm run test:e2e`

CI (`.github/workflows/ci.yml`, Ubuntu 24.04) runs both jobs on PRs.

## Latest reported results (Codex delivery report, `fix/onboarding-once`, 27 Oct 2026)
219 backend tests, 74 browser tests, 9 web unit tests passed. (Reported by the agent; not re-run for this document.)

## What the tests cover

Backend coverage includes API permissions/tenant isolation, auth/MFA/reset, invitations, uploads/storage, worker receipt checks, audit chains, invoices, N/A, reports, onboarding and the no-model boundary. Browser tests exercise synthetic workflows, accessibility, role-specific navigation, upload/questionnaire, manual review, tasks/pipeline, workspaces, invoices/reports, onboarding persistence/retry, sidebar/theme and client response privacy.

Web sign-in and MFA controls were deliberately removed for the demo; restore their browser assertions with auth in phase 3. Synthetic browser tests and routed API fixtures do not prove live storage, email, authentication or hosting behavior. Historical reported counts above are not current verification.

## Release checklist
- [ ] All CI jobs pass; exact commands and results in the report.
- [ ] New endpoints have permission-denial and cross-firm tests.
- [ ] Upload/auth changes include failure cases.
- [ ] No secrets, no real client data in diff, screenshots or logs.
- [ ] Docs updated to match behaviour.
- [ ] UI: before/after screenshots desktop light, desktop dark, phone (375 px); keyboard and reduced motion checked.
- [ ] If separately authorized, preview deployment verified for both roles; restore auth before live.
- [ ] Synthetic test data undone/reset (e.g. progress back to 0/32, demo walkthroughs as required).
- [ ] Separate live authorization, restored auth and Abdullah visual approval before any live operation.

Automated passes do not certify accessibility, security or regulatory compliance.
