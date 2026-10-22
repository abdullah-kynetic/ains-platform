# Workflow app build handoff

## Delivered in task order

1. **Branch consolidation:** historical phases 2–8 reviewed and merged separately, with direct
   model code removed. Phase 0/portal-review were already ancestors. See
   [consolidation-summary.md](consolidation-summary.md) for the phase-by-phase limitations.
2. **Canonical checklist:** all 34 stable request IDs in `data/checklist/aml_bd_v1.yaml`.
   Backend views read it; the web build generates its bundled demo inventory from that source.
   Rubric placeholders remain empty for Quinton. Restricted requests accept no portal evidence.
3. **Central upload:** searchable picker, multiple files, editable destinations, confirmation,
   per-file errors/receipts and SHA-256. Real ingestion is restricted to `/Shared/AINS-Dev`;
   synthetic browser tests use a local metadata mock and backend tests use fake Egnyte storage.
4. **Client flows:** questionnaire, no-activity confirmations, pending N/A review, applicable
   requests, collection progress, follow-ups and fixed neutral replacement messages.
5. **Auditor flows:** assigned-client dashboard, documents/versions per request, separate
   applicability and manual evidence decisions, internal notes, actor/change history and
   report-readiness blockers. New evidence invalidates stale assessments. No model inference.
6. **Polish:** shared spacing/typography/colors, searchable grouped requests, guided upload,
   keyboard/mobile navigation, focus return, contrast, reduced motion and loading/retry/empty
   states. Browser tests cover automated WCAG-tagged rules, 375px layouts, keyboard navigation,
   sign-in failure, error recovery and core client/auditor flows. This is not accessibility certification.

Each task PR describes changes, tests and unfinished work. All merges use real merge commits;
main is pushed after every merge. Task 1 used one PR per historical phase as requested.

## See the synthetic demo locally

```bash
cd web
npm ci
NEXT_PUBLIC_USE_MOCKS=true npm run dev
```

Open `http://localhost:3000`. Start with the questionnaire, inspect the checklist, then use
Upload center with **synthetic files only**. The labeled role switch opens the auditor demo.
Demo mode stores receipt metadata and synthetic review decisions in this browser, not file
bytes. It never sends credentials or email; sign-in offers an explicit Open synthetic demo button.
Use a fresh browser profile to reset demo state. Real API mode never permits demo role switching.

Cloudflare deployment configuration is documented in [web/README.md](../web/README.md).
The public Worker is a synthetic browser demo only; the production prerequisites below
still apply to a deployment connected to real accounts or storage.

## Validation

```bash
uv run ruff check .
uv run pytest -q
uv run python scripts/evaluate_synthetic.py
cd web
npm run lint
npm run typecheck
npm run build
npx playwright install chromium
npm run test:e2e
```

Postgres migrations through `a105_manual_review` were applied to a separate synthetic
verification database; `alembic check` found no missing operations. CI is pinned to Ubuntu
24.04 so the rolling runner-image migration does not change browser system dependencies.

## Before real deployment—not implied complete by these task merges

- Quinton must review the request wording, applicability conditions and allowed evidence types,
  then supply the rubric. Empty rubric fields are intentional, not invented audit standards.
- Provision invited users, auditor MFA and engagement assignments; configure the approved
  magic-link email sender, session secret, HTTPS cookie settings, CORS and recovery process.
- Existing legacy request keys need an explicit reviewed migration. Initialization only accepts
  empty assigned engagements and does not guess mappings or overwrite records.
- Validate live Egnyte access with synthetic files only. This build's storage verification used
  a fake Egnyte client, not a live account. Storage-only worker receipts are not content review.
- Review production operations: tenant authorization, backups, retention, malware scanning,
  monitoring, deployment and recovery. Application change history is not tamper-proof external storage.
- Review report content/templates and signing procedures. Readiness means workflow review
  completeness, not a clean opinion or signed report; existing draft exports remain unsigned.
- The external automation pipeline is intentionally unconnected. Any future adapter needs its
  own security/data contract, and must not process restricted material through this app.
