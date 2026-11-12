# data - canonical checklist and synthetic firms

One job: hold the 34-item checklist source and synthetic data. No real client documents, ever.

## Inputs
- Reference (every run): `checklist/aml_bd_v1.yaml`
- Reference (every run): `synthetic/README.md`
- Reference (every run): `../docs/kb/22-checklist-catalog.md`

## Process
1. `checklist/aml_bd_v1.yaml` is the only source of the request IDs; backend and web catalogs derive from it.
2. Leave rubric placeholders empty for Quentin.
3. Add only mock or synthetic files under `synthetic/`.

## Outputs
- Updated YAML or synthetic fixtures with matching tests (`../tests/test_checklist_catalog.py`, `../tests/test_synthetic_firms.py`).

## Check
`uv run pytest -q tests/test_checklist_catalog.py tests/test_synthetic_firms.py`.
