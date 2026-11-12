# docs - catalog of project documents

One job: point to the right document. Stores no rules of its own.

## Inputs
- Reference (every run): `ICM-PLAN.md`
- Reference (every run): `kb/00-INDEX.md`
- Reference (every run): `STATUS.md`

## Process
1. Current scope and rules: `PROJECT-BRIEF.md` (it wins over older text), then `../CLAUDE.md`.
2. Product and design: `PRD.md`, `ARCHITECTURE.md`, `DATABASE.md`, `SECURITY.md`, `DESIGN_SYSTEM.md`.
3. AI: `AI-ANALYSIS.md`, `kb/16-ai-features-finra-chatbot.md`, `kb/17-model-policy.md`.
4. Pipelines as stage contracts: [pipelines/ai-analysis](pipelines/ai-analysis/CONTEXT.md).
5. Historical, kept for context: `lanes/`, `handoff/`, `delivery/`, `BUILD-PLAN.md`.
6. Do not delete or move a doc without checking what links to it.

## Outputs
- Updated catalog entries when a doc is added.

## Check
`uv run pytest -q tests/test_icm_workspace.py`.
