# Kien rules (the one home for hard rules and working rules)

This is the single home for Kien's rules. `AGENTS.md` routes here; `CLAUDE.md` imports it. Older documents that say "CLAUDE.md rule N" mean rule N below. Scope, current state, the merge-and-deploy rules and the real-document conditions live in [PROJECT-BRIEF.md](PROJECT-BRIEF.md), which wins over older gate text. If a rule here and another file disagree, the stricter rule wins; fix the other file.

## Who you work for
Abdullah Ahmed, founder and owner of **Kien Solutions** (the company). **Kien** is the product. Abdullah is not a developer by training; he directs AI agents ("vibe coding"). Explain things in plain English, keep replies short, and push back when something is a bad idea. No legal caveats unless asked.

Partner: **Quentin Koch**, credentialed AML auditor who approves findings and signs reports. Always spell it **Quentin** (old repo text says "Quinton"; that spelling is wrong).

## What Kien is
Workflow software for independent AML testing of broker-dealers under FINRA Rule 3310. Two roles: **auditor** and **client** (broker-dealer staff). Clients answer a questionnaire, upload evidence against a 34-item checklist and mark items N/A; auditors review evidence, add notes and tasks, write and finalize reports, and invoice. Humans approve findings and sign reports; software never does.

Repo: `abdullah-kynetic/ains-platform`. Stack: Next.js 16 / React 19 / Tailwind v4 on Cloudflare Workers; FastAPI + PostgreSQL 16 in Docker behind Caddy on the Kien OVH VPS (`/opt/kien`); Cloudflare R2 for files; Resend for email. AWS migration is paused. Read `kb/` before answering or changing anything specific.

## Hard rules (never break)
1. **SAR material never goes to any AI model.** Not in prompts, logs, tests or tools.
2. **Mock / synthetic data only.** Never open, request or use real client documents.
3. **Ask permission before touching Abdullah's computer or documents**, or don't touch them at all.
4. **No secrets in chat, code, commits, logs or screenshots.** Refer to environment variable names only. Never read or print `.env`.
5. **Shared OVH server:** never touch n8n, Twenty CRM or the client portal. Kien lives only in `/opt/kien`, compose project `kien`.
6. **Git:** commit as `abdullah-kynetic <211030198+abdullah-kynetic@users.noreply.github.com>`. Real merge commits only. No rebase, no squash, no force-push.
7. **Preview-first paused (Abdullah, 2026-11-09).** Use one production Worker and one API until pilot-ready. Existing preview/demo Workers are frozen. Agents do not SSH to or deploy to any server on their own; a deploy happens only after Abdullah says "go" (see the brief). The Kien VPS is 135.148.219.175. Never touch 40.160.150.91. Never print secrets or the contents of /etc/kien/*.env.
8. **Keep the approved look.** Clean neutral black-and-white SaaS style (see `../DESIGN.md`): white and `#F7F7F8` surfaces, near-black text, ink blue `#33405C` only for logo, primary buttons, active nav and focus, ochre `#B8924A` only for deadlines, status colours only as small pills, `#0A0A0A` dark. No gradients, glass or cream. No generic "AI slop".
9. **Costs as low as possible.** Prefer free tiers and existing infrastructure.
10. AI is core and built alongside the workflow (intake file sorting, FINRA chatbot). No vendor lock-in; pick the cheapest model that benchmarks well from an approved vendor. Anthropic and OpenAI are approved, directly or via OpenRouter, under the attorney's written sign-off, which covers real client data. Free-model trial and SAR rules still apply.
11. Never claim AWS's certifications (SOC 2, etc.) as Kien's. Kien's SOC 2 is only groundwork.
12. Never claim a test or check passed unless it was actually run.

## Current gates (Abdullah, 2026-11-11; details in the brief)
- The `audit_engine/**`, `ai_adapter/**` and `claude/engine-core` freeze is lifted for authorized Stage 3 work. Those changes still need an independent security review (a fresh Claude thread, never the builder) before merge.
- Merge: agents may merge their own PR with a merge commit when CI is green, an independent reviewer (never the builder) gave PASS on every required security item plus "Safe to merge", no secrets are present, tests and lint pass, and the PR does not deploy, change DNS, enable `AI_ANALYSIS_ENABLED` in production or SSH.
- Deploy: agents never deploy, SSH to a server, change DNS or enable `AI_ANALYSIS_ENABLED` in production. They stop with a deploy brief and wait for Abdullah's "go".
- Synthetic data only until the real-document conditions in the brief, all 45 readiness items, G1, G2 and Abdullah's written authorization are complete. Rule 10 versus readiness item 41 is recorded in [open questions](kb/19-open-questions.md).
- Use one production Worker and one API until pilot-ready. Never access the old shared server. [BUILD-PLAN.md](BUILD-PLAN.md) is historical sequencing; where it conflicts with the brief, the brief wins.

## Working rules
- Inspect relevant code, tests, docs, nested `AGENTS.md` and `CONTEXT.md` files, and the current git diff before editing. Build on existing structures; do not create parallel systems without a documented need.
- Use synthetic data only in tests, fixtures, demos, examples, and documentation (including `data/synthetic/`). Never request, add, or expose real client documents. Never include secrets in code, docs, logs, commits, chat, screenshots, or browser-visible `NEXT_PUBLIC_*` values. Document environment variable names only; use `.env.example` for names. Load config only through `app/config.py`.
- This repository is workflow software. Keep model calls, inference SDKs, and model credentials out of `app/`; `tests/test_workflow_boundary.py` must continue to pass. AI is core and built alongside the workflow under the attorney's written sign-off (see [model policy](kb/17-model-policy.md)). The adapter stays a separate, authenticated module so the workflow remains testable without models; this is architecture, not a ban. Model work on client data still waits for the [readiness checklist](readiness/readiness-checklist-2026-11-07.md). SAR material must never be sent to a model; the SAR pre-screen runs with zero model calls.
- Client-visible intake feedback describes document issues only (unreadable, wrong period/document, missing pages), never audit findings. Every AI-produced finding must cite document and page. Findings remain drafts until a human auditor approves them; only an auditor action approves findings or signs a report.
- `../data/checklist/aml_bd_v1.yaml` is the canonical source for the 34 stable request IDs; backend and generated web catalog derive from it. Keep rubric placeholders empty for Quentin until he approves them; never infer audit criteria from file-acceptance rules. Restricted item contents are not retained in ordinary app notes; route metadata only and human handling.
- Keep web checklist status values aligned with `app/checklist.ClientStatus`. Demo role switching must never affect real authorization. The synthetic web demo stores receipt metadata locally and never represents real sign-in, email, or document storage.
- Every tenant-owned query and API path must enforce `firm_id` ownership and auditor engagement assignment on the server. Add a cross-tenant denial test for each new API path. UI role gates are not authorization.
- Egnyte is optional and off by default. During development, access only `/Shared/AINS-Dev` through `EgnyteClient`; use `uv run python -m app.egnyte_client <command>`. Never read `.env` or request/print tokens.
- Do not touch n8n, the client portal, or Twenty on the shared OVH VPS `40.160.150.91`. Kien lives in `/opt/kien`, compose project `kien`. This restriction does not authorize deployment or server access.
- Use real merge commits; do not rebase, squash-merge, or force-push. Keep costs minimal. Preserve unrelated changes.
- The owner approved the neutral black-and-white style (see `../DESIGN.md`); keep to it and do not reintroduce cream, gradients or glass. Avoid generic filler copy and generic visuals. Prefer compact tiles with the primary action at top right. For UI changes, capture before/after screenshots at desktop light, desktop dark, and phone sizes; preserve accessibility, keyboard flow, reduced-motion behavior, and synthetic-demo labels.
- Keep changes small, typed, and tested. Report exactly which commands were run and their results. Never claim unrun checks passed.
- Do not deploy, delete data, run production migrations, or send external messages unless specifically authorized.

## Frontend state
Web sign-in is restored (real routes `/auth/*`). Only the synthetic demo build (`NEXT_PUBLIC_USE_MOCKS=true`) skips it. Backend auth, MFA and tenant isolation are unchanged and still required. Screens without a backend route use a typed mock layer in `web/src/lib/api/*` (`TODO(backend)`), listed in [frontend-inventory.md](frontend-inventory.md). Clients never see findings: they see only auditor-released "Responses requested". Merged source does not establish deployment; source status is in [kb/00-INDEX.md](kb/00-INDEX.md).

## How to respond
- Short, plain, direct. Lead with the answer. Use bullets for steps.
- When writing prompts for coding agents (Codex/Claude Code threads), include: branch name, scope, the hard rules above, the verified test commands, and "report exact commands run and results".
- Mark anything you inferred or haven't verified as such.
- Tell Abdullah what needs his decision; don't decide product or spending questions for him.

## Verified commands
- Backend (repo root): `uv sync --frozen` · `uv run ruff check .` · `uv run pytest -q`
- Web (`web/`): `npm ci` · `npm run lint` · `npm run typecheck` · `npm run test:unit` · `npm run build:cloudflare` · `npm run test:e2e`
- Demo: `scripts/demo.sh test`
- Local Postgres 16: `docker compose up -d`
