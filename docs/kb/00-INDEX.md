# Kien — Master Knowledge Base

Refreshed 2 Nov 2026 against source through `d822ce1` (PR #72). Abdullah Ahmed owns the product; Quentin Koch approves findings and signs reports.

## Current source and runtime

PRs #53–#60 and #64–#72 are merged: invoicing, reversible/direct N/A, editable reports, onboarding, shadcn layout and the neutral redesign. The next stacked backend slice adds `a116_client_profiles` for client metadata and contacts; the cleanup base is `a115_user_onboarding`. These are source facts, not deployment verification.

Client profiles/contacts and engagement summaries have real API clients outside mock mode in the next backend slice. Other new auditor tabs and client Responses requested, Report and Invoices screens use typed synthetic mocks. [Frontend inventory](../frontend-inventory.md) identifies every route and backend contract. Existing backend workflows remain distinct from those new mock screens.

Web sign-in is restored on the IMPL-4 branch (not merged or deployed until its PR is reviewed). The synthetic demo build still opens without sign-in. Backend auth, MFA, firm isolation and engagement assignment remain enforced.

The approved look is neutral black-and-white; see [DESIGN.md](../../DESIGN.md). Ink is limited to brand/actions/navigation/focus; ochre marks deadlines; status colors are small pills.

OVH is the current owner-supplied backend target, Cloudflare hosts the frontend and R2 stores files. AWS is planned migration work. No server or deployed resource was inspected during this refresh. Historical deployment versions are not current-state evidence.

AI is core and built alongside the workflow under the attorney's written sign-off (see [17-model-policy.md](17-model-policy.md)). Real client data waits for the [readiness checklist](../readiness/readiness-checklist-2026-11-07.md). This index does not authorize live deployments, server operations or merges. Preview deployments also require an explicit step. Current status: [docs/STATUS.md](../STATUS.md). Vision: [docs/VISION.md](../VISION.md).

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
