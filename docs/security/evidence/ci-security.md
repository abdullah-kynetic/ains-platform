# L1-2 security workflow verification

2026-11-09; base `49ee4b8`, plus L1-1 image hardening (PR #94).

Implemented all nine scanner jobs on pull requests and main pushes. Jobs fail on
nonzero exits, do not fail-fast, install frozen dependencies and upload sanitized
structured finding metadata. Actions are pinned to resolved commit SHAs; checkout
credentials are not persisted. No scanner finding is suppressed. Native suppression
files and inline bypasses are rejected before scanning. CodeQL's private-repository
cost exception is recorded with reason, owner and expiry in accepted-risks.md.

Independent review reran 42 targeted tests and Ruff, and identified a JS/TS comment
bypass in the first policy matcher. Corrected it to handle `//` and `/*` as well as
`#`, with tests for all three forms. No full acceptance PASS is claimed.

## Scanner execution

Actual scanners were invoked using `bash scripts/security/scan.sh <scanner>`.
The runner uses the plan's commands with JSON report switches and containerized
binaries for Gitleaks, TruffleHog and Trivy. Tool caches were redirected to /tmp
because the executor's home is read-only; no credentials were read or changed.

| Scanner | Result |
| --- | --- |
| pip-audit | PASS, exit 0, no reported vulnerabilities |
| npm audit production dependencies | PASS, exit 0 |
| Gitleaks git history | FAIL, exit 1, three generic-api-key matches |
| TruffleHog verified secrets | PASS, exit 0 |
| Trivy filesystem | FAIL, exit 1; no parsed findings; unresolved tool/runtime failure |
| Trivy image | FAIL, exit 1; no parsed findings; unresolved build/runtime failure |
| Semgrep | FAIL, exit 2; no parsed findings; unresolved tool/runtime failure |
| Bandit | PASS, exit 0 |
| zizmor | FAIL, exit 14, High dangerous-triggers for image workflow_run |

Gitleaks metadata (no matched content retained):

- tests/test_auditor_assignment.py, historical commit 51be7fac893258ac8f2ffc36dd7c364d778f65ec
- web/src/lib/invoice-api.ts, historical commit 57b52e5fdaf600c91c135a8469929005daa191dd
- web/e2e/auditor.spec.ts, historical commit f8f40ffc09048724429bec5ae66189dcd5ce3dff

BLOCKED(owner): Triage historical matches securely. No git history rewrite or native
ignore was added. Lane 2 owns tests/test_auditor_assignment.py. Current-source edits
cannot remove historical matches from `gitleaks git`.

BLOCKED(owner): Resolve/accept the workflow_run trigger finding with an expiry-backed
policy, or change the required after-CI image publication architecture. The workflow
restricts publication to trusted main pushes, but zizmor still flags the trigger.

BLOCKED(environment): Trivy and Semgrep must complete successfully before merge.
No unavailable scan is counted as a clean scan. CI and independent acceptance
remain required. No server, deployment or AI changes were made.

Targeted final verification: `UV_CACHE_DIR=/tmp/kien-uv-cache uv run pytest -q tests/test_ci_security.py tests/test_image_workflow.py`: 46 passed. Ruff, bash syntax and suppression-policy checks passed.


## Final full gate

- `UV_CACHE_DIR=/tmp/kien-uv-cache uv sync --frozen`: PASS, 67 packages.
- `UV_CACHE_DIR=/tmp/kien-uv-cache uv run ruff check .`: PASS.
- `UV_CACHE_DIR=/tmp/kien-uv-cache uv run pytest -q`: 412 passed, 11 skipped,
  one Starlette dependency deprecation warning (184.77 seconds).
- In web: `npm ci --cache /tmp/kien-npm-cache`, `npm run lint`,
  `npm run typecheck`: PASS; `npm run test:unit`: 23 passed.
- `NEXT_PUBLIC_USE_MOCKS=true npm run build:cloudflare` and
  `npm run build:cloudflare:production`: PASS. Both completed with a read-only-home
  Wrangler log warning; no deployment was run.
- `npx playwright install --with-deps chromium`: failed (root elevation unavailable).
  Browser-only installation failed (download domain denied).
- `PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=/usr/bin/chromium npm run test:e2e:live`:
  8 passed using the real local backend and synthetic users.
- `PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=/usr/bin/chromium npm run test:e2e`:
  80 passed, 2 failed. The two production-style tenant-host checks show a cloud proxy
  Domain forbidden page, not the application. No policy bypass was attempted.

PRs: #94 (image) and #97 (security), neither merged. Latest hosted Security checks:
pip-audit, npm, TruffleHog and Bandit passed; Gitleaks, Semgrep and zizmor failed;
Trivy jobs were pending at the checkpoint. Full hosted CI remained pending.

L1-3 through L1-9 are not implemented in this change; no inventory counts or live
product coverage are claimed. Package and lockfile ownership still awaits Lane 2's
#37 handoff. No edits were made outside Lane 1's owned paths.
