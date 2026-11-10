# L1-7: documents, activity and pipeline

Synthetic local FastAPI/SQLite and Chromium only. No deployment, email delivery,
upload/storage or client-data proof. Baseline UI: main `083daba`; after UI: this
PR. Each of documents/activity/pipeline has before/after captures at desktop
1280×900 light/dark and phone 390×844. Tables and pipeline retain local scrolling.
Screenshots were captured separately from the browser regression suite.

## Behavior

- Documents use the assigned-auditor workspace receipts. Missing uploader/page
  metadata is unavailable, not invented. Receipt without feedback means Received,
  not an audit approval. Client access returns 403; another firm returns 404.
- Activity uses the server's latest 20 assigned-engagement events and filters to
  the current engagement. This is a recent feed, not the complete immutable log.
- Pipeline uses existing persisted stage transitions. Due soon counts actual
  calendar deadlines (including today); assigned initials come from server data.
  Controls disable while saving. Completion still requires the existing signature
  gate. No client confirmation/invoice transition is claimed.
- Untouched demo-backed screens retain their synthetic notice until their own
  contract wiring lands. Full remaining work is listed in STATUS's Requests to
  Lane 2. This slice does not complete L1-7 or remove all production mocks.

## Verification

- `uv sync --frozen`, `uv run ruff check .`: passed.
- `uv run pytest -q`: 462 passed, 11 skipped (PostgreSQL unavailable locally).
- `uv run pytest -q tests/test_deploy_live_fixture.py`: 1 passed.
- `npm ci`, `npm run lint`, `npm run typecheck`: passed.
- `npm run test:unit`: 28 passed.
- `NEXT_PUBLIC_USE_MOCKS=true npm run build:cloudflare` and
  `npm run build:cloudflare:production`: passed with writable XDG_CONFIG_HOME.
- `PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=/usr/bin/chromium npm run test:e2e:live`:
  14 passed, including three new real-backend flows, role and cross-firm denial.
- Independent review round 2: PASS; reran fixture, Ruff, lint and typecheck.
- `npx playwright install --with-deps chromium`: blocked by root authentication;
  installed system Chromium used successfully.
- Local scan wrapper: pip-audit, npm, Gitleaks, TruffleHog, Bandit passed. Zizmor
  passed offline. Trivy fs passed on the repository-source snapshot with the
  existing accepted-risks policy; scanning the entire local workspace also sees
  Moto test keys in ignored `.venv`, which is absent in hosted filesystem scanning.
  Container Trivy commands did not complete locally; Semgrep registry access was
  denied. Hosted Security and full mock browser results are recorded in the PR.

The synthetic fixture uses a finite 1200 requests/minute for shared loopback
traffic; production settings and account lockout are unchanged. This suite does
not replace the rate-limit/lockout security proofs.
