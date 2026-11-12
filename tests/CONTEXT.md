# tests - backend test map

One job: prove behaviour and isolation for `app/`, `ai_adapter/` and `audit_engine/`. Fake models only; synthetic data only.

## Inputs
- Reference (every run): `../docs/TESTING.md`
- Reference (every run): `route_inventory.txt`
- Reference (every run): `conftest.py`
- Working (this task): the `test_*.py` for the area changed; `security/` for controls

## Process
1. Add a cross-tenant denial test for every new API path.
2. Never call a real model or print secrets. `test_workflow_boundary.py` must keep passing.
3. Postgres-only tests (`*_postgres.py`) run in CI.

## Outputs
- Test modules; evidence files in `../docs/security/evidence/` for security controls.

## Check
`uv run pytest -q` from the repo root. Never report a test as passed unless it ran.
