# 01_select-evidence - choose which files are considered

One job: build the list of documents for one engagement, each with its linked checklist item.

## Inputs
- Reference (every run): `../../../../app/api/ai_analysis.py`
- Reference (every run): `../../../../tests/test_ai_analysis.py`
- Reference (every run): `../../../../data/checklist/aml_bd_v1.yaml`

Do NOT load: real documents, other firms' data, `../../../../web/`.

## Process
1. Gate first: signed-in auditor, `AI_ANALYSIS_ENABLED` on, engagement assigned to the caller's firm.
2. Query documents and links filtered by `firm_id` and `engagement_id`.
3. A file linked to a restricted item (AML-BD-017, AML-BD-025) is never read from storage.
4. Order files with a draft rubric first; the engine caps the run at 8 files.
5. Only one run per engagement at a time; a second request while one is running gets 409 and makes no model call.

## Outputs
- A list of `DocInput` handed to stage 02 (in memory; nothing is written).

## Check
Tests prove another firm's engagement is denied and restricted files are not read: `uv run pytest -q tests/test_ai_analysis.py`.
