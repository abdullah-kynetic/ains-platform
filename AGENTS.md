# Kien coding-agent guide

Kien by Kien Solutions is workflow software for independent AML testing of broker-dealers under FINRA Rule 3310. Quentin is the AINS partner and auditor who approves findings and signs reports. Historical repository text spells the name “Quinton”; use “Quentin” in current product context.

## Read before product work

Read [PRD](docs/PRD.md), [Design System](docs/DESIGN_SYSTEM.md), [Architecture](docs/ARCHITECTURE.md), [Database](docs/DATABASE.md), [Security](docs/SECURITY.md), [Code Style](docs/CODE_STYLE.md), and [Testing](docs/TESTING.md). Keep them mutually consistent. Treat explicit unresolved items as unresolved, not approved design.

## Stage gates (Abdullah, 2026-11-09)

Use one production Worker and one API until pilot-ready; existing preview/demo
Workers are frozen. Preview-first is paused for this phase. Code agents never
access servers; Lane C operates the new VPS. Never access the old shared server.
`audit_engine/**`, `ai_adapter/**` and `claude/engine-core` remain frozen until
Abdullah signs off the Stage 2 security audit (G2), enabling Stage 3 (G3).
No model calls in Stage 1. See [BUILD-PLAN.md](docs/BUILD-PLAN.md) for sequencing.
These current stage gates supersede earlier "built alongside" scheduling text.

## Working rules

- Inspect relevant code, tests, docs, nested `AGENTS.md` files, and the current git diff before editing. Build on existing app structures; do not create parallel systems without a documented need.
- Use synthetic data only in tests, fixtures, demos, examples, and documentation. Never request, add, or expose real client documents. Never include secrets in code, docs, logs, commits, chat, screenshots, or browser-visible `NEXT_PUBLIC_*` values. Document environment variable names only.
- This repository is workflow software. Keep model calls, inference SDKs, and model credentials out of `app/`; `tests/test_workflow_boundary.py` must continue to pass. AI is core and built alongside the workflow under the attorney's written sign-off (see docs/kb/17-model-policy.md). The adapter stays a separate, authenticated module so the workflow remains testable without models; this is architecture, not a ban. Model work on client data still waits for the readiness checklist (docs/readiness/readiness-checklist-2026-11-07.md). SAR material must never be sent to a model; the SAR pre-screen runs with zero model calls.
- Client-visible intake feedback may describe document issues only (unreadable, wrong period/document, missing pages), never audit findings. Findings remain drafts until a human auditor approves them; only an auditor action can sign a report.
- `data/checklist/aml_bd_v1.yaml` is the canonical source for 34 stable request IDs; backend and generated web catalog derive from it. Keep rubric placeholders empty for Quentin until he approves them; never infer audit criteria from file-acceptance rules. Restricted item contents are not retained in ordinary app notes; route metadata only and human handling.
- Keep web checklist status values aligned with `app/checklist.ClientStatus`. Demo role switching must never affect real authorization. The synthetic web demo stores receipt metadata locally and never represents real sign-in, email, or document storage.
- Every tenant-owned query and API path must enforce `firm_id` ownership and auditor engagement assignment on the server. Add cross-tenant denial coverage for new API paths. UI role gates are not authorization.
- Egnyte is optional and off by default. During development, access only `/Shared/AINS-Dev` through `EgnyteClient`; use `uv run python -m app.egnyte_client <command>`. Never read `.env` or request/print tokens.
- Do not touch n8n, the client portal, or Twenty on the shared OVH VPS `40.160.150.91`. Kien lives in `/opt/kien`, compose project `kien`. This restriction does not authorize deployment or server access.
- Use real merge commits; do not rebase, squash-merge, or force-push. Keep costs minimal. Preserve unrelated changes.
- The owner approved the neutral black-and-white style (see DESIGN.md); keep to it and do not reintroduce cream, gradients or glass. Avoid generic filler copy and generic visuals. Prefer compact tiles with the primary action at top right. For UI changes, capture before/after screenshots at desktop light, desktop dark, and phone sizes; preserve accessibility, keyboard flow, reduced-motion behavior, and synthetic-demo labels.
- Keep changes small, typed, and tested. Report exactly which commands were run and their results. Never claim unrun checks passed.
- Git commit identity: `abdullah-kynetic <211030198+abdullah-kynetic@users.noreply.github.com>`.
- Do not deploy, delete data, run production migrations, or send external messages unless specifically authorized.

## Frontend demo phase

Web sign-in is restored; only the synthetic demo build skips it. See [docs/frontend-inventory.md](docs/frontend-inventory.md) for screens, routes and every mocked `TODO(backend)` call. Clients never see findings: they see only auditor-released response requests. Backend authentication, MFA and tenant isolation are unchanged and still required.

## Verified commands

See [Code Style](docs/CODE_STYLE.md) and [Testing](docs/TESTING.md) for commands verified in project configuration. Backend includes `uv run ruff check .`, `uv run pytest -q`; web commands are run from `web/` and include `npm run lint`, `npm run typecheck`, `npm run test:unit`, `npm run build:cloudflare`, and `npm run test:e2e`.

## Session sequence

1. Read the seven documents above and applicable nested instructions; inspect implementation and repository state.
2. Summarize requirements, acceptance criteria, risks, and unresolved decisions before proposing product changes.
3. Make the smallest scoped change in existing structures.
4. Run relevant verified checks. UI work needs browser/accessibility coverage and before/after screenshots in desktop light, desktop dark, and phone sizes.
5. Review the full diff for secrets, real client data, scope creep, and inaccurate docs; report changes, exact checks and results, and limitations.
