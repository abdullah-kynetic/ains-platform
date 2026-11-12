# AI analysis pipeline (Stage 3, off by default)

The flow in one line: select the engagement's evidence, block SAR before anything leaves, ask a free model for drafts, re-validate the reply, then an auditor accepts, edits or rejects. Behaviour reference: [AI-ANALYSIS.md](../../AI-ANALYSIS.md). Safety rules: [RULES.md](../../RULES.md).

| Stage | Job | Code that does it today |
|---|---|---|
| `01_select-evidence` | pick firm-scoped files and their checklist items | `app/api/ai_analysis.py` |
| `02_sar-prescreen` | skip restricted, SAR-tagged and SAR-content files | `audit_engine/engine.py`, `ai_adapter/guards.py` |
| `03_draft` | call an allowlisted free model through the gateway | `audit_engine/engine.py`, `ai_adapter/` |
| `04_validate` | keep only drafts that cite a real document and page | `audit_engine/engine.py`, `ai_adapter/schemas.py` |
| `05_auditor_review` | auditor Accept, Edit or Reject | `app/api/ai_analysis.py` |

This pipeline documents code that already exists; it adds no code path. Each stage's `CONTEXT.md` names its inputs, what it must never do, and the check. Status of a run lives in the database (`AiRun`, `AiDraft`) and the audit log, not in files here.

Nothing moves to the next stage until the last stage's check holds. Clients never see runs, drafts or findings.
