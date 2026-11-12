# 02_sar-prescreen - block SAR material before any model call

One job: skip every file that is restricted, SAR-tagged or mentions SAR content. Zero model calls here.

## Inputs
- Reference (every run): `../../../../audit_engine/engine.py`
- Reference (every run): `../../../../ai_adapter/guards.py`
- Reference (every run): `../../../../tests/test_ai_review_137.py`

Do NOT load: model credentials, real documents.

## Process
1. Skip restricted checklist items and SAR tags.
2. Scan the file name, then the extracted text (PDF, DOCX, TXT, CSV) with `sar_content_reason`; it folds case, punctuation, look-alikes and zero-width characters.
3. Skip scans and unsupported types (XLSX, DOC, XLS) and record why.
4. Every skip is shown to the auditor with a plain reason. The scan runs again inside the adapter.

## Outputs
- Skipped files with codes (`restricted_item`, `sar_tag`, `sar_content`, and extraction codes), stored on the run.

## Check
`uv run pytest -q tests/test_ai_review_137.py tests/test_ai_analysis.py` pass, including the attacker cases. A person still reviews the file set before a real-document run.
