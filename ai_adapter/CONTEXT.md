# ai_adapter - authenticated model gateway

One job: the only place a model is called. A separate service from `app/`; off by default.

## Inputs
- Reference (every run): `../CLAUDE.md`
- Reference (every run): `../docs/AI-ANALYSIS.md`
- Reference (every run): `../docs/kb/17-model-policy.md`
- Reference (every run): `allowlist.json`
- Working (this task): `guards.py`, `service.py`, `schemas.py` and `../tests/test_ai_adapter.py`

Do NOT load: `../app/`, `../web/`, real documents.

## Process
1. Only exact `:free` OpenRouter IDs from `allowlist.json`; price-check to zero on every call; no paid fallback.
2. SAR text never reaches a model. `guards.sar_content_reason` runs here and again in the engine.
3. Every call carries firm, engagement and user, and verifies document ownership.
4. Log metadata only, never document text. Keys come from environment variable names only.

## Outputs
- Code and tests only. Any change needs an independent security review before merge (see the brief).

## Check
`uv run pytest -q tests/test_ai_adapter.py tests/test_ai_review_137.py` plus the full suite, all green; a reviewer who is not the builder signs off.
