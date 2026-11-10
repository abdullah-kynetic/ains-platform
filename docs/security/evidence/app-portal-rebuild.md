# Firm portal rebuild: independent security review

Date: 2026-11-09. Candidate source: `7d40a96` (subsequently merged current main).
Review performed by a separate agent that did not write the changes, in two rounds.
Final source/security regression verdict: PASS. Full CI and PostgreSQL execution
remain required before merge; this is not live-host or operational evidence.

| Control | Evidence |
| --- | --- |
| Tenant denial | Central authenticated-user dependency binds firm/session to the resolved portal; tests exercise own/wrong portal, conflicting hosts, client/auditor host mismatch, invitation and magic-link sessions. New public branding route returns name/logo only; other firm records are omitted. |
| Wrong portal sign-in | 403 before cookie issuance; tests assert no `Set-Cookie`. |
| Cookie isolation | HttpOnly, Secure under production settings, SameSite=Lax, no Domain. The shared API cookie still requires server-side firm binding. |
| Exact CORS | Known firm origins plus configured exact origins; rejects unknown/reserved/lookalike origins and malformed authorities. No wildcard reflection. Preflight validates methods and headers; PUT/DELETE supported. |
| Links and logos | Platform auditor email links use the auditor host. Logos reject network paths, missing hosts, credentials and invalid ports. |
| Migrations | Added upgrade/downgrade/re-upgrade test for a118/a119; preserves synthetic firm data and checks slug constraint. Local PostgreSQL test skipped (no binaries); CI execution required. |

Independent regression command:

`PYTHONPATH=. /workspace/ains-platform/.venv/bin/python -m pytest -q tests/test_portal_tenancy.py -k 'portal_url_template or logo_rejects or malformed_origins or preflight_enforces' tests/test_portal_tenancy_postgres.py`

Result: 11 passed, 20 deselected (migration excluded by the filter).
Separate `tests/test_portal_tenancy_postgres.py`: 1 skipped, no local binaries.
`git diff --check`: passed.

Author post-fix focused command (with `UV_CACHE_DIR=/tmp/kien-uv-cache`):

`uv run pytest -q tests/test_portal_tenancy.py tests/test_portal_tenancy_postgres.py tests/test_route_isolation.py tests/test_origin_check.py tests/test_backend_api.py tests/test_deployment_migration.py`

Result: 106 passed, 1 skipped, one existing Starlette deprecation warning.
`uv run ruff check .`: passed.

Earlier baseline review run was interrupted; no complete result is claimed for it.
No server access, Terraform, DNS changes, real client data, model calls or live email sends.
