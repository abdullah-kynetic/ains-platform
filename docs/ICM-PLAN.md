# ICM plan: what Interpretable Context Methodology means for Kien

Status: plan, 2026-11-12. PR 1 (#139) and PR 2 are open; PR 3 follows. Requested by Abdullah ("do it first, ASAP"). Behaviour of the product does not change in any step.

## What ICM is (read from the two source repos, including `SKILL.md` and the templates)
ICM ([RinDig/Interpretable-Context-Methodology](https://github.com/RinDig/Interpretable-Context-Methodology), [RinDig/icm-architect](https://github.com/RinDig/icm-architect), MIT) is a way to lay out a **workspace that AI agents read**. Folders carry the structure instead of orchestration code:

- A small entry file (`AGENTS.md`, under about 60 lines) says where things live and where to go for a task.
- Every working folder has a `CONTEXT.md` contract: **Inputs** (exact paths, working vs reference), **Process**, **Outputs**, one **Check**.
- Stable rules ("factory") are kept apart from per-run artifacts ("product").
- Each step ends at a check (a person, a script or a test) before the next step runs.
- One home per fact; links beat copies; a cold agent should find its way with the entry file plus two reads ("walk test").

ICM is about the **agent-facing layer** of a repo. It does not say to renumber or move application source code, and it names its own limits: it fits sequential, checked, repeatable work, not high-concurrency serving.

## What this means for Kien (decisions)
1. **We do not move or rename `app/`, `web/`, `ai_adapter/`, `audit_engine/`, `migrations/` or `tests/`.** Python import paths, Alembic, Next.js routing, the Cloudflare build, CI and the deploy scripts all depend on them. Moving them would risk the Friday demo for no benefit ICM asks for. Every code folder instead gets a `CONTEXT.md` contract.
2. **Kien's real ICM pipeline is the audit engagement and the AI analysis flow**, and they already have numbered stages with human checks. We write them down as contracts (PR 3) so agents load only what a stage needs.
3. **Entry file diet** (PR 2, after PR #138 lands, because it edits the same files): `AGENTS.md` becomes the short router; the hard rules move to one home, `docs/RULES.md` (the factory); `CLAUDE.md` becomes a pointer (`@AGENTS.md`) plus nothing else. Rules are not weakened, only de-duplicated.
4. **Docs get a catalog, not a reshuffle** (PR 2): `docs/CONTEXT.md` classifies each doc as current, reference or historical. No deletions. Files with live referrers stay put.
5. **No new tooling dependency.** A small test (`tests/test_icm_workspace.py`) checks that every link and input path in the ICM files resolves. It is the "walk test" in CI form.

## Target layout (additions only)
```
AGENTS.md              entry router (PR 2 shrinks it)
CLAUDE.md              pointer (PR 2)
CONTEXT.md             root map: the engagement flow and where each folder fits (PR 1)
app/CONTEXT.md         API contract (PR 1)
ai_adapter/CONTEXT.md  model gateway contract (PR 1)
audit_engine/CONTEXT.md  analysis engine contract (PR 1)
web/CONTEXT.md         web app contract (PR 1)
tests/CONTEXT.md       test map and commands (PR 1)
scripts/CONTEXT.md     scripts contract (PR 1)
data/CONTEXT.md        checklist and synthetic data contract (PR 1)
docs/CONTEXT.md        docs catalog (PR 1 draft, PR 2 final)
docs/RULES.md          the hard rules, one home (PR 2)
docs/pipelines/ai-analysis/   five stage contracts mapped to code and tests (PR 3)
```

## Migration steps (each is its own reviewable PR off `main`, no behaviour change)
| PR | Content | Check |
|---|---|---|
| 1 | This plan, root and folder `CONTEXT.md` contracts, link test | `uv run pytest -q tests/test_icm_workspace.py`, full backend suite, ruff |
| 2 | Slim `AGENTS.md`, `docs/RULES.md`, `CLAUDE.md` pointer, docs catalog (after #138 merges) | Every old rule found in `RULES.md`; link test; reviewer diffs rule text |
| 3 | `docs/pipelines/ai-analysis/` stage contracts | Each contract's input paths and test names exist; link test |

## What stays as is
All source layout, the 34-item checklist YAML, migrations, deploy files, CI, the approved look, the Friday demo flow (`scripts/demo.sh test`). Frozen folders: only markdown is added next to the code, no code edits.

## Walk test (how we judge done)
A fresh agent with no memory can, from `AGENTS.md` plus at most two reads, say where it is, which folder owns a task, which commands verify it, and which rules apply, and the link test passes.
