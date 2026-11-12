# scripts - demo, seeds and local backends

One job: reproducible synthetic demos and test backends. Nothing here deploys unless Abdullah says go.

## Inputs
- Reference (every run): `../DEMO.md`
- Reference (every run): `../CLAUDE.md`
- Working (this task): the script being changed, for example `demo.sh` or `e2e_backend.py`

## Process
1. Synthetic data only. `demo.sh` refuses a Postgres `DATABASE_URL`.
2. Do not touch `../deploy/` or compose files from a demo script.
3. `deploy-demo.sh` and anything touching a server needs Abdullah's explicit go.

## Outputs
- Scripts and their tests in `../tests/test_deploy_scripts.py`, `../tests/test_e2e_seed.py`.

## Check
`scripts/demo.sh test` runs the seven-step demo headless; `uv run pytest -q` covers the script tests.
