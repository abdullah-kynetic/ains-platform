# Project instructions for coding agents

AINS: AI-native financial regulatory audit platform. First service: FINRA Rule 3310 independent AML tests for broker-dealers. A credentialed auditor (Quinton) approves findings and signs every report.

## Stack
- Python 3.12, FastAPI, Pydantic v2, pydantic-settings, httpx, tenacity
- uv for packages (`uv sync`, `uv run pytest`, `uv run ruff check .`)
- Postgres 16 locally via `docker compose up -d`
- Client documents in Egnyte (Internal API app, OAuth password flow)
- This repository is workflow software only. No direct model calls; a separate pipeline may
  connect later through an authenticated backend adapter.
- Next.js 16 (TypeScript, Tailwind v4) client portal in `web/` (npm); talks to the API via `NEXT_PUBLIC_API_URL`

## Layout
```
app/
  main.py            FastAPI app (/health)
  config.py          Settings loaded from environment variables
  auth/              Backend sessions, invite-only password/magic-link sign-in, auditor MFA
  api/               Tenant-scoped engagement and document endpoints
  checks/            Storage receipt verification only; no model inference
  database/          SQLAlchemy models and session management
  documents/         Upload validation, hashing, and guarded Egnyte ingestion
  egnyte_client/     Egnyte API client (client.py), path guard (paths.py), CLI (cli.py)
  reports/           Unsigned DOCX/PDF draft report generation
  worker.py          Durable Postgres-backed async document-check worker
  checklist/         Checklist items and client-facing statuses
tests/               pytest suite (synthetic data only)
web/                 Next.js client portal (see web/README.md)
data/synthetic/      Fake documents for tests and demos
templates/report/    Swappable draft-report layout and required notices
.github/workflows/   CI: backend ruff + pytest; web lint + typecheck + build
```

## Rules
- **Never read, print, log, or commit `.env` or any secret.** Use `.env.example` for variable names. Load config only through `app/config.py`.
- **Egnyte: only touch paths under `/Shared/AINS-Dev` (`EGNYTE_DEV_ROOT`) during development.** Always go through `EgnyteClient` (it enforces the path guard).
- **To use Egnyte, run the CLI**: `uv run python -m app.egnyte_client whoami | ls <path> | mkdir <path> | upload <local> <remote> | download <remote> <dest>`. It loads credentials itself; never read `.env` and never run `get-token` or print tokens.
- **Synthetic data only** in tests, fixtures, and `data/synthetic/`. Never add or request real client documents.
- **SAR or SAR-indicating files are never sent to any AI model.** Detect and route them to the human-only lane before any AI call.
- **Intake feedback to clients must never reveal audit findings.** Only document-level issues (unreadable, wrong period, wrong document, missing pages).
- **Every AI-produced finding must cite document and page.** No citation, no finding.
- **Humans approve findings and sign reports.** Code never marks a finding final or a report signed without an auditor action.
- **Tenant isolation is mandatory.** Every tenant-owned query must filter by `firm_id`; client users see only their firm and auditors only assigned engagements. Add a cross-tenant denial test for each new API path.
- **`web/`**: no secrets in `NEXT_PUBLIC_*` vars (they ship to the browser); mock data must be synthetic; status values must match `app/checklist.ClientStatus`; never show audit findings in client UI. Run `npm run lint && npm run build` in `web/` before committing.
- **Portal roles**: client routes expose only neutral intake state; `/auditor` contains internal checks and finding drafts and must remain protected by backend auditor authorization as well as the UI role gate.
- Keep changes small, typed, and tested. Run `uv run ruff check .` and `uv run pytest` before committing.
