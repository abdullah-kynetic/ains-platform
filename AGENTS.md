# Kien agent guide (entry file)

Kien by Kien Solutions is workflow software for independent AML testing of broker-dealers under FINRA Rule 3310. Quentin (never "Quinton") is the partner who approves findings and signs reports. This file only routes; it holds no rules.

## Read first, every task
1. [docs/RULES.md](docs/RULES.md): hard rules, working rules, gates, how to respond.
2. [docs/PROJECT-BRIEF.md](docs/PROJECT-BRIEF.md): scope, state, merge-and-deploy rules, real-document conditions. It wins over older text.
3. [CONTEXT.md](CONTEXT.md): the engagement flow and which folder owns what.

## Where things live
| Folder | Contract |
|---|---|
| `app/` | [API and database](app/CONTEXT.md) |
| `web/` | [Next.js app](web/CONTEXT.md) |
| `audit_engine/`, `ai_adapter/` | [engine](audit_engine/CONTEXT.md), [model gateway](ai_adapter/CONTEXT.md) |
| `tests/`, `scripts/`, `data/` | [tests](tests/CONTEXT.md), [scripts](scripts/CONTEXT.md), [data](data/CONTEXT.md) |
| `docs/` | [catalog](docs/CONTEXT.md); product docs: [PRD](docs/PRD.md), [Architecture](docs/ARCHITECTURE.md), [Database](docs/DATABASE.md), [Security](docs/SECURITY.md), [Code Style](docs/CODE_STYLE.md), [Testing](docs/TESTING.md), [Design System](docs/DESIGN_SYSTEM.md) |

Knowledge base: [docs/kb/00-INDEX.md](docs/kb/00-INDEX.md). Why the repo is laid out this way: [docs/ICM-PLAN.md](docs/ICM-PLAN.md).

## Verified commands
Backend (repo root): `uv run ruff check .`, `uv run pytest -q`. Web (in `web/`): `npm run lint`, `npm run typecheck`, `npm run test:unit`, `npm run build:cloudflare`. Demo: `scripts/demo.sh test`. Full list in [docs/RULES.md](docs/RULES.md).

## Session sequence
1. Read the three files above and the `CONTEXT.md` of the folder you will touch; inspect the diff.
2. Summarize requirements, risks and unresolved decisions before proposing product changes.
3. Make the smallest scoped change in existing structures.
4. Run the folder's Check; UI work also needs before/after screenshots (desktop light, dark, phone).
5. Review the full diff for secrets, real client data, scope creep and wrong docs; report exact commands and results.

`CLAUDE.md` imports this file and the rules, so Claude Code loads both automatically.
