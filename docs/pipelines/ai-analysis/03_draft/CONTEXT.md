# 03_draft - ask a free model for drafts

One job: send the surviving text to the gateway and get structured drafts back. Only the gateway talks to a model.

## Inputs
- Reference (every run): `../../../../ai_adapter/allowlist.json`
- Reference (every run): `../../../../ai_adapter/guards.py`
- Reference (every run): `../../../../audit_engine/rubric_draft.yaml`
- Reference (every run): `../../../../docs/kb/17-model-policy.md`

Do NOT load: `../../../../app/` internals; the `app/` package never imports the adapter.

## Process
1. Call only exact `:free` IDs from the allowlist; price-check to zero on each call; no routers, no paid fallback.
2. Try the second model only after an upstream failure, never after a policy refusal.
3. The rubric is a DRAFT until Quentin approves it; use it as drafting context only.
4. Log metadata only (firm, engagement, user, model, outcome), never text.

## Outputs
- Raw structured findings returned to stage 04.

## Check
`uv run pytest -q tests/test_ai_adapter.py` with the fake model; CI never calls a real model.
