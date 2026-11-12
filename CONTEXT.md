# Kien workspace map

Kien is AML independent-testing workflow software. This file routes you to the folder that owns a task; each folder's own `CONTEXT.md` holds its contract. Rules: [docs/RULES.md](docs/RULES.md). Plan for this layout: [docs/ICM-PLAN.md](docs/ICM-PLAN.md).

## The flow, in order
| Step | What happens | Owner folder |
|---|---|---|
| 1 | Firm and client onboarding, sign-in | `app/auth/`, `web/src/app/` |
| 2 | Checklist sent, questionnaire, reasoned N/A | `app/checklist/`, `data/checklist/` |
| 3 | Client uploads and links evidence; scan and fingerprint | `app/documents/`, `app/storage/` |
| 4 | Auditor review, notes, tasks, response requests | `app/api/auditor.py`, `app/api/findings.py` |
| 5 | Optional AI drafts (off by default), auditor Accept / Edit / Reject | `audit_engine/`, `ai_adapter/`, `app/api/ai_analysis.py` |
| 6 | Report, sign-off, invoice | `app/reports/`, `app/api/signoff.py`, `app/invoicing.py` |

Every step ends at a human or test check. Software never approves a finding or signs a report.

## Route by task
| If the task is | Go to |
|---|---|
| an API route or database change | [app/CONTEXT.md](app/CONTEXT.md) |
| a screen or web client call | [web/CONTEXT.md](web/CONTEXT.md) |
| AI analysis, SAR guard, model gateway | [audit_engine/CONTEXT.md](audit_engine/CONTEXT.md), [ai_adapter/CONTEXT.md](ai_adapter/CONTEXT.md) |
| running or adding tests | [tests/CONTEXT.md](tests/CONTEXT.md) |
| demo, seeds, e2e backend | [scripts/CONTEXT.md](scripts/CONTEXT.md) |
| checklist IDs or synthetic firms | [data/CONTEXT.md](data/CONTEXT.md) |
| anything about scope, rules, deploy | [docs/PROJECT-BRIEF.md](docs/PROJECT-BRIEF.md) |

Status is what exists on `main` plus the open PRs. Merged source does not mean deployed.
