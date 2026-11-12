# app - the FastAPI workflow backend

One job: serve the auditor and client API with firm isolation. Owns all tenant data. Never calls a model.

## Inputs
- Reference (every run): `../CLAUDE.md`
- Reference (every run): `../docs/SECURITY.md`
- Reference (every run): `../docs/DATABASE.md`
- Reference (every run): `../docs/kb/07-api-reference.md`
- Working (this task): the route file under `api/` and its test under `../tests/`

Do NOT load: `../web/`, `../ai_adapter/`, other routes' files.

## Process
1. Every tenant-owned query filters by `firm_id`; auditors see only assigned engagements.
2. Add a cross-tenant denial test for each new route and add the route to `../tests/route_inventory.txt`.
3. Load config only through `config.py`. No secrets, no model SDKs, no `ai_adapter` import (`../tests/test_workflow_boundary.py` enforces this).
4. Schema changes need an Alembic migration in `../migrations/`.

## Outputs
- Code in `api/`, `auth/`, `checklist/`, `documents/`, `reports/`, `storage/`, `database/`; tests in `../tests/`.

## Check
`uv run ruff check .` and `uv run pytest -q` from the repo root, both green.
