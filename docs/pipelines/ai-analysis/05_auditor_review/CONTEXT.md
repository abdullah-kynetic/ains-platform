# 05_auditor_review - a person decides

One job: the auditor accepts, edits or rejects each pending draft. Software never approves.

## Inputs
- Reference (every run): `../../../../app/api/ai_analysis.py`
- Reference (every run): `../../../../tests/test_ai_analysis.py`
- Reference (every run): `../../../../tests/test_responses_requested.py`

## Process
1. Accept copies the draft into an ordinary internal draft finding; it still needs the existing approval and "Request response" release.
2. Edit and Reject change only the draft's own state and are audit-logged.
3. No client route returns runs, drafts or findings.
4. A double-click must not start two runs (tracked as follow-up work in the AI demo PR, not here).

## Outputs
- Draft state `accepted`, `edited` or `rejected`, and `ai_draft.*` audit-log entries.

## Check
The auditor is the check. Tests prove clients and other firms cannot read drafts: `uv run pytest -q tests/test_ai_analysis.py tests/test_responses_requested.py`.
