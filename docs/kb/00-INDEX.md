# Kien — Master Knowledge Base (index)

Written 29 Oct 2026 from repo `abdullah-kynetic/ains-platform`, branch `fix/onboarding-once` (commit `02c480c`, 27 Oct 2026), which stacks every unmerged PR (#53–#60) on top of `main`. Items marked **(inferred)** or **(unverified)** were not confirmed from code.

## Main vs preview — read this first
`main` (the branch Claude Code clones) is at merge `12f6f70` (PR #52), Alembic head `a111`. **PRs #53–#60 are open and NOT on `main`.** They are stacked in this order and shown only on preview addresses:

| PR | Branch | What it adds | Where to see it |
| --- | --- | --- | --- |
| #53 | `feat/auditor-invoicing` | Auditor invoicing v1 (migration `a112`) | preview |
| #54 | `fix/monday-polish` | Theme/sidebar polish, invoices shared within issuer firm | preview |
| #55 | `feat/checklist-na` | Reversible checklist N/A, progress over 32 items (migration `a113`) | preview |
| #56 | `feat/auditor-reports` | Editable auditor reports, finalize/reopen/print (migration `a114`) | preview |
| #57 | `feat/onboarding` | First sign-in walkthrough (migration `a115`) | preview |
| #58 | `fix/na-client-auditor-access` | Client marks N/A directly; assigned auditor full workspace access | preview |
| #59 | `feat/shadcn-layout` | Compact shadcn layout, Impeccable, `PRODUCT.md`/`DESIGN.md`, `.impeccable/` | layout.kiensolutions.com |
| #60 | `fix/onboarding-once` | Walkthrough only once per account; preview/layout Worker configs | preview + layout |

Consequences for anyone working from `main`:
- Files such as `app/invoicing.py`, `app/api/invoices.py`, `app/api/reports.py`, `app/auth/onboarding.py`, migrations `a112`–`a115`, `PRODUCT.md`, `DESIGN.md`, `.impeccable/`, `web/wrangler.preview.jsonc` and `web/wrangler.layout.jsonc` do **not** exist yet.
- On `main`, N/A is still the older flow: the client proposes N/A in the questionnaire and the auditor approves it (`/questionnaire/items/{item_id}/na-review`).
- The shared OVH backend already runs the stacked code (`02c480c`) and its database is at `a115`, so production API ≠ `main`. Do not run `main`'s migrations "down" against it.
- New feature branches that depend on #53–#60 must branch from `fix/onboarding-once` (or wait until the stack is merged); branches that don't can start from `main`.
- Throughout these files, **Live** means on `main`; **Preview (#NN)** means only on the open stack.


| File | Topic |
| --- | --- |
| `/CLAUDE.md` (repo root) | Project instructions (formerly PROJECT_INSTRUCTIONS.md) |
| 01-product-overview-prd.md | What Kien is, users, journeys, requirements |
| 02-feature-inventory.md | Every feature as built, with status (live / preview / planned) |
| 03-architecture.md | System diagram, request and data flow |
| 04-tech-stack-and-vendors.md | Exact stack, every service and vendor, environments |
| 05-data-model.md | Database tables and migrations |
| 06-auth-and-permissions.md | Sign-in, MFA, roles, who can do what |
| 07-api-reference.md | Every API route |
| 08-design-system.md | Colours, layout geometry, Impeccable |
| 09-sop-dev-workflow.md | How work gets built (agents, git, PRs) |
| 10-sop-deploy-rollback.md | How to deploy and roll back |
| 11-sop-testing-qa.md | Tests, commands, visual review |
| 12-sop-security-compliance.md | Security and compliance rules |
| 13-ops-runbook.md | Day-to-day operations |
| 14-aws-migration-plan.md | Move to AWS outline |
| 15-roadmap-build-order.md | What gets built next, in order |
| 16-ai-features-finra-chatbot.md | AI intake sorting and FINRA chatbot design |
| 17-model-policy.md | Which AI models and why |
| 18-costs.md | Running costs (estimates) |
| 19-open-questions.md | Decisions still needed |
| 20-glossary.md | Plain-English glossary |
| 21-claude-code-orchestration.md | Parallel workstreams and ready-to-paste thread prompts |
| 22-checklist-catalog.md | The 34 checklist requests |
