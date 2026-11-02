# CLAUDE.md — Kien project instructions for Claude Code

This file is read automatically by Claude Code. It is kept consistent with [`AGENTS.md`](AGENTS.md) (the guide for all coding agents); if the two ever disagree, the stricter rule wins and the conflict should be fixed in both files.

## Who you work for
Abdullah Ahmed, founder and owner of **Kien Solutions** (the company). **Kien** is the product. Abdullah is not a developer by training; he directs AI agents ("vibe coding"). Explain things in plain English, keep replies short, and push back when something is a bad idea. No legal caveats unless asked.

Partner: **Quentin Koch** — credentialed AML auditor who approves findings and signs reports. Always spell it **Quentin** (old repo text says "Quinton"; that spelling is wrong).

## What Kien is
Workflow software for independent AML testing of broker-dealers under FINRA Rule 3310. Two roles: **auditor** and **client** (broker-dealer staff). Clients answer a questionnaire, upload evidence against a 34-item checklist and mark items N/A; auditors review evidence, add notes and tasks, write and finalize reports, and invoice. Humans approve findings and sign reports; software never does.

Repo: `abdullah-kynetic/ains-platform`. Stack: Next.js 16 / React 19 / Tailwind v4 on Cloudflare Workers; FastAPI + PostgreSQL 16 in Docker behind Caddy on a shared OVH server (`/opt/kien`); Cloudflare R2 for files; Resend for email. AWS migration (us-east-1) is planned. Read the knowledge base in `docs/kb/` before answering or changing anything specific.

## Hard rules (never break)
1. **SAR material never goes to any AI model.** Not in prompts, logs, tests or tools.
2. **Mock / synthetic data only.** Never open, request or use real client documents.
3. **Ask permission before touching Abdullah's computer or documents**, or don't touch them at all.
4. **No secrets in chat, code, commits, logs or screenshots.** Refer to environment variable names only. Never read or print `.env`.
5. **Shared OVH server:** never touch n8n, Twenty CRM or the client portal. Kien lives only in `/opt/kien`, compose project `kien`.
6. **Git:** commit as `abdullah-kynetic <211030198+abdullah-kynetic@users.noreply.github.com>`. Real merge commits only. No rebase, no squash, no force-push.
7. **Preview first.** New features deploy to preview; live (`kien-demo-live`) only after Abdullah approves the visuals. Design experiments go on their own separate address.
8. **Keep the approved look.** Clean neutral black-and-white SaaS style (see `DESIGN.md`): white and `#F7F7F8` surfaces, near-black text, ink blue `#33405C` only for logo, primary buttons, active nav and focus, ochre `#B8924A` only for deadlines, status colours only as small pills, `#0A0A0A` dark. No gradients, glass or cream. No generic "AI slop".
9. **Costs as low as possible.** Prefer free tiers and existing infrastructure.
10. **AI features come last** (intake file sorting, then FINRA chatbot). No vendor lock-in; pick the cheapest model that benchmarks well from an approved vendor (attorney verbally approved Anthropic and OpenAI).
11. Never claim AWS's certifications (SOC 2, etc.) as Kien's. Kien's SOC 2 is only groundwork.
12. Never claim a test or check passed unless it was actually run.

## How to respond
- Short, plain, direct. Lead with the answer. Use bullets for steps.
- When writing prompts for coding agents (Codex/Claude Code threads), include: branch name, scope, the hard rules above, the verified test commands, and "report exact commands run and results".
- Mark anything you inferred or haven't verified as such.
- Tell Abdullah what needs his decision; don't decide product or spending questions for him.

## Branch status: `main` vs preview (important)
PRs #53–#60 (invoicing, reversible/direct N/A, editable reports, first-sign-in walkthrough, shadcn layout, preview Worker configs) and the nine-part design series #64–#72 (neutral style, Today view, engagement workspace, firm settings, client Responses requested, host audiences, removed web sign-in, docs) are merged into `main`. Source status and implementation boundaries are recorded in [`docs/kb/00-INDEX.md`](docs/kb/00-INDEX.md). Merged source does not establish deployment.

## Frontend state
Web sign-in is removed for the demo phase (`AUTH_REMOVED` in `web/src/lib/api.ts`; `TODO(auth)` marks what to restore). **Restore it before any live deploy or real data.** Backend auth, MFA and tenant isolation are unchanged. Screens without a backend route use a typed mock layer in `web/src/lib/api/*` (`TODO(backend)`), listed in `docs/frontend-inventory.md`. Clients never see findings: they see only auditor-released "Responses requested".

## Repo rules for coding agents (also in AGENTS.md)
- Never read, print, log or commit `.env` or any secret; use `.env.example` for variable names. Load config only through `app/config.py`. No secrets in `NEXT_PUBLIC_*` vars (they ship to the browser).
- Synthetic data only in tests, fixtures, demos and `data/synthetic/`.
- No model calls, inference SDKs or model credentials in `app/`; `tests/test_workflow_boundary.py` must keep passing. Future AI goes in a separate, authenticated adapter.
- Client-visible intake feedback describes document issues only (unreadable, wrong period/document, missing pages), never audit findings. Every AI-produced finding must cite document and page. Only an auditor action approves findings or signs a report.
- Tenant isolation: every tenant-owned query filters by `firm_id`; auditors see only assigned engagements. Add a cross-tenant denial test for each new API path. UI role gates are not authorization.
- `data/checklist/aml_bd_v1.yaml` is the canonical source of the 34 request IDs. Keep web status values aligned with `app/checklist.ClientStatus`. Leave rubric placeholders empty for Quentin.
- Egnyte is optional and off. In development, touch only `/Shared/AINS-Dev` through `EgnyteClient` (`uv run python -m app.egnyte_client <command>`); never print tokens.
- Do not deploy, delete data, run production migrations or send external messages unless the task explicitly authorizes it.
- Keep changes small, typed and tested. Report exact commands run and their results.

## Verified commands
- Backend (repo root): `uv sync --frozen` · `uv run ruff check .` · `uv run pytest -q`
- Web (`web/`): `npm ci` · `npm run lint` · `npm run typecheck` · `npm run test:unit` · `npm run build:cloudflare` · `npm run test:e2e`
- Local Postgres 16: `docker compose up -d`

## Where to read more
Repo docs (source of truth for behaviour on `main`):
- [`AGENTS.md`](AGENTS.md) — coding-agent guide and session sequence
- [`README.md`](README.md) · [`docs/PRD.md`](docs/PRD.md) · [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) · [`docs/DATABASE.md`](docs/DATABASE.md) · [`docs/SECURITY.md`](docs/SECURITY.md) · [`docs/CODE_STYLE.md`](docs/CODE_STYLE.md) · [`docs/TESTING.md`](docs/TESTING.md) · [`docs/DESIGN_SYSTEM.md`](docs/DESIGN_SYSTEM.md) · [`docs/deploy-aws.md`](docs/deploy-aws.md)
- `PRODUCT.md`, `DESIGN.md`, `.impeccable/` — merged with #59

Knowledge base (`docs/kb/`, written 29 Oct 2026; plain-English overview, SOPs and plans):
- [`00-INDEX.md`](docs/kb/00-INDEX.md) — Kien — Master Knowledge Base (index)
- [`01-product-overview-prd.md`](docs/kb/01-product-overview-prd.md) — Product overview and PRD
- [`02-feature-inventory.md`](docs/kb/02-feature-inventory.md) — Feature inventory (as built)
- [`03-architecture.md`](docs/kb/03-architecture.md) — Architecture
- [`04-tech-stack-and-vendors.md`](docs/kb/04-tech-stack-and-vendors.md) — Tech stack, systems and vendors
- [`05-data-model.md`](docs/kb/05-data-model.md) — Data model
- [`06-auth-and-permissions.md`](docs/kb/06-auth-and-permissions.md) — Authentication and permissions
- [`07-api-reference.md`](docs/kb/07-api-reference.md) — API reference (FastAPI, from route decorators on `fix/onboarding-once`)
- [`08-design-system.md`](docs/kb/08-design-system.md) — Design system
- [`09-sop-dev-workflow.md`](docs/kb/09-sop-dev-workflow.md) — SOP — Development workflow
- [`10-sop-deploy-rollback.md`](docs/kb/10-sop-deploy-rollback.md) — SOP — Deploy and rollback
- [`11-sop-testing-qa.md`](docs/kb/11-sop-testing-qa.md) — SOP — Testing and QA
- [`12-sop-security-compliance.md`](docs/kb/12-sop-security-compliance.md) — SOP — Security and compliance
- [`13-ops-runbook.md`](docs/kb/13-ops-runbook.md) — Ops runbook (current OVH setup)
- [`14-aws-migration-plan.md`](docs/kb/14-aws-migration-plan.md) — AWS migration plan (outline)
- [`15-roadmap-build-order.md`](docs/kb/15-roadmap-build-order.md) — Roadmap and build order
- [`16-ai-features-finra-chatbot.md`](docs/kb/16-ai-features-finra-chatbot.md) — AI features (built last)
- [`17-model-policy.md`](docs/kb/17-model-policy.md) — Model policy
- [`18-costs.md`](docs/kb/18-costs.md) — Costs (all figures are ESTIMATES unless marked)
- [`19-open-questions.md`](docs/kb/19-open-questions.md) — Open questions (need a decision)
- [`20-glossary.md`](docs/kb/20-glossary.md) — Glossary (plain English)
- [`21-claude-code-orchestration.md`](docs/kb/21-claude-code-orchestration.md) — Claude Code orchestration plan
- [`22-checklist-catalog.md`](docs/kb/22-checklist-catalog.md) — The 34 checklist requests
