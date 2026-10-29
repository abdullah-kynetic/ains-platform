# SOP — Development workflow

## Who does what
- **Coding agents (Codex CLI, Claude Code threads) do the work end to end**: read docs, branch, code, test, screenshot, push, deploy to preview, write a report.
- **Orchestrator (Grok Bot / Claude Code lead)** writes the prompt, picks the model and effort, does the final check, opens and merges PRs.
- **Abdullah** does not review code or PRs. He **only reviews visuals** on preview. Nothing goes live until he approves.
- Codex default: `gpt-6.1-sol`, high effort, for code. Cursor cloud agents are not used.

## Step by step
1. **Brief.** Write a prompt with: goal, branch name (`feat/…`, `fix/…`, `docs/…`), base branch (stack on the latest open branch if the work depends on it), scope limits, hard rules, verified commands, deliverables (report path, screenshots).
2. **Agent reads first:** `AGENTS.md`, `CLAUDE.md`, `docs/kb/00-INDEX.md`, `PRODUCT.md` and `DESIGN.md` (only once #59 is merged, or on the preview stack), `docs/PRD.md`, `ARCHITECTURE.md`, `DATABASE.md`, `SECURITY.md`, `CODE_STYLE.md`, `TESTING.md`, `DESIGN_SYSTEM.md`, nested `AGENTS.md`.
3. **Build small.** Reuse existing structures. Typed, tested. New API path → cross-tenant denial test. Docs updated in the same PR (PRD/ARCHITECTURE/DATABASE/SECURITY/TESTING sections).
4. **Run checks** (see `11-sop-testing-qa.md`). Report exact commands and results. Never claim unrun checks.
5. **Commit** as `abdullah-kynetic <211030198+abdullah-kynetic@users.noreply.github.com>`. Push the branch.
6. **Deploy to preview** (and backend if needed) per `10-sop-deploy-rollback.md`, with a DB backup and a rollback file first.
7. **PR.** `gh` on the box can't create PRs (token permissions); the orchestrator opens them with the GitHub connector. Stacked PRs reference their base.
8. **Abdullah reviews visuals** on preview.kiensolutions.com (or the experiment address).
9. **Merge** with **real merge commits** in stack order. No rebase, squash or force-push.
10. **Deploy live** (`kien-demo-live`) and verify with both demo logins.

## Rules
- Preview first; live only after visual approval. Design experiments on their own address.
- Never touch n8n, Twenty or the client portal on the OVH box.
- Synthetic data only. No secrets anywhere.
- Keep costs minimal. Leave all AI features until the end.
- Before a destructive git step (reset --hard, force push) — don't. If ever needed, ask Abdullah first.
- Tell Abdullah every time a backend or frontend agent reports back.
