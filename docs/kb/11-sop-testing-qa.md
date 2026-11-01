# SOP — Testing and QA

> **Branch status (checked 29 Oct 2026):** `main` is at merge `12f6f70` (PR #52), Alembic head `a111`. PRs **#53–#60 are NOT merged into `main`**; they are a stack (#53 → #54 → #55 → #56 → #57 → #58 → #59 → #60) on top of `main` and are visible only on preview (preview.kiensolutions.com; #59 on layout.kiensolutions.com). Anything tagged **Preview (#NN)** below is not in a fresh `main` checkout. The shared OVH backend already runs the stacked code (`02c480c`, DB at `a115`), so the API serves these routes even though `main` does not contain them.

## Commands (verified in CI config)
Backend (repo root): `uv sync --frozen` · `uv run ruff check .` · `uv run pytest -q` · targeted: `uv run pytest tests/test_workflow_boundary.py -q` · `uv run python scripts/evaluate_synthetic.py`
Web (`web/`): `npm ci` · `npm run lint` · `npm run typecheck` · `npm run test:unit` · `npm run build:cloudflare` · `npx playwright install --with-deps chromium` · `npm run test:e2e`

CI (`.github/workflows/ci.yml`, Ubuntu 24.04) runs both jobs on PRs.

## Latest reported results (Codex delivery report, `fix/onboarding-once`, 27 Oct 2026)
219 backend tests, 74 browser tests, 9 web unit tests passed. (Reported by the agent; not re-run for this document.)

## What the tests cover (preview stack; `main` has 20 pytest files and 19 Playwright specs — invoices, N/A, reports, onboarding and impeccable tests arrive with #53–#60)
- `tests/`: 25 pytest files — API, tenant isolation, auth/MFA/reset, invitations, uploads and path guard, S3 storage (moto), worker, audit chain (Postgres), invoices (incl. Postgres race test), N/A, reports, onboarding, monitoring scrubbing, workflow boundary (no model SDKs in `app/`).
- `web/e2e/`: 25 Playwright specs — accessibility (axe), sign-in, upload, questionnaire, checklist N/A, auditor, tasks, pipeline, workspaces, invoices, reports, audit log, onboarding, sidebar resize, header/sidebar, tenant host, redesign, impeccable, sentry, demo.
- E2E runs in synthetic mock mode; it does not prove live R2, Resend, OVH or Worker behaviour.

## Release checklist
- [ ] All CI jobs pass; exact commands and results in the report.
- [ ] New endpoints have permission-denial and cross-firm tests.
- [ ] Upload/auth changes include failure cases.
- [ ] No secrets, no real client data in diff, screenshots or logs.
- [ ] Docs updated to match behaviour.
- [ ] UI: before/after screenshots desktop light, desktop dark, phone (375 px); keyboard and reduced motion checked.
- [ ] Deployed preview verified with both demo logins (client and auditor).
- [ ] Synthetic test data undone/reset (e.g. progress back to 0/32, demo walkthroughs as required).
- [ ] Abdullah approved visuals before live.

Automated passes do not certify accessibility, security or regulatory compliance.
