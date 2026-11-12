# audit_engine - AI analysis engine (drafts only)

One job: turn selected evidence into pending draft findings that cite document and page. Never approves or signs.

## Inputs
- Reference (every run): `../CLAUDE.md`
- Reference (every run): `../docs/AI-ANALYSIS.md`
- Reference (every run): `rubric_draft.yaml` (DRAFT, needs Quentin's approval; not final)
- Working (this task): `engine.py`, `extract.py`, `rubric.py` and `../tests/test_ai_analysis.py`

Do NOT load: `../app/` internals beyond `../app/api/ai_analysis.py`, real documents.

## Process
1. Skip restricted checklist items and SAR content before reading or sending anything.
2. Extract PDF text, DOCX, TXT, CSV only; skip scans, XLSX, DOC, XLS and report why.
3. Every draft cites a document and page that exist; extra fields discard the reply.
4. Leave the draft rubric marked DRAFT. Do not edit checklist rubric placeholders.

## Outputs
- Pending drafts returned to `../app/api/ai_analysis.py`; auditor Accept / Edit / Reject is the next check.

## Check
`uv run pytest -q tests/test_ai_analysis.py tests/test_ai_adapter.py` plus the full suite; independent security review before merge.
