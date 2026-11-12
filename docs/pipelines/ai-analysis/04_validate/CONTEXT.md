# 04_validate - keep only cited, well-formed drafts

One job: re-validate the model's reply before it is stored.

## Inputs
- Reference (every run): `../../../../ai_adapter/schemas.py`
- Reference (every run): `../../../../audit_engine/engine.py`
- Reference (every run): `../../../../tests/test_ai_adapter.py`

## Process
1. Accept only fixed JSON with the three draft kinds; extra fields (status, sign, approve) discard the whole reply.
2. Keep a draft only if it cites the document that was sent and a page that exists.
3. Store each kept draft as `pending`, with model and item.

## Outputs
- `AiDraft` rows in `pending` state plus an `ai_analysis.run` audit-log entry (ids and counts only).

## Check
`uv run pytest -q tests/test_ai_adapter.py tests/test_ai_analysis.py`: uncited or out-of-range drafts never appear.
