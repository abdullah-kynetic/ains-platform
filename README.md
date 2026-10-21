# AINS Platform

AINS is an AI-native financial regulatory audit firm. Our software does the legwork; a credentialed auditor (Quinton) makes the calls and signs every report. The first service is the FINRA Rule 3310 independent AML test for broker-dealers; more regulatory audits will follow.

This repo holds the audit engine (Python 3.12, FastAPI, Pydantic) and the client portal
(Next.js 16 in `web/`). Client documents are stored in Egnyte via an Internal API app.

## Authoritative checklist

The [M&A broker-dealer AML request list](docs/checklist/aml-ma-bd-request-list.md) preserves all
34 requests from the user-supplied Word document, with stable reference IDs and source issues
for Quinton to review. Use this reference when implementing the checklist; do not substitute the
portal's synthetic demo items. SAR filings and decision records require controlled human handling.

The versioned catalog is `data/checklist/aml_bd_v1.yaml`; see
[the implementation review](docs/checklist-summary.md) for all six sections and outstanding
decisions. Auditor-only `POST /auditor/engagements` creates a new firm and draft with a frozen
34-item snapshot. At `/auditor/manage`, the assigned auditor reviews the snapshot, records review
notes, and explicitly approves publication before clients can see it. Required written
representations remain requested after a negative questionnaire answer; N/A approval requires
an uploaded representation and auditor confirmation. Follow-up requests are released separately.

## Setup

```bash
# 1. Install uv: https://docs.astral.sh/uv/
uv sync                          # creates .venv and installs deps (incl. dev)

# 2. Local Postgres
docker compose up -d --wait
uv run alembic upgrade head

# 3. Environment
cp .env.example .env             # fill in values locally; never commit .env

# 4. Run
uv run uvicorn app.main:app --reload    # http://localhost:8000/health
uv run python -m app.worker             # durable document-check worker
uv run pytest
uv run ruff check .
```

The backend owns authentication and uses an HTTP-only `ains_session` cookie. Users must already
be invited in the database; there is no public sign-up endpoint. Client users may sign in with a
password or magic link, and auditor accounts require TOTP MFA. Set `SESSION_SECRET` to a long,
random value before using sign-in. Magic-link token delivery is an injectable backend adapter and
must be connected to an approved email provider before that sign-in method is enabled outside tests.
See [authentication deployment setup](docs/authentication-setup.md) for the remaining hosting,
invitation, MFA-enrollment, and live-cookie validation work. The public demo role switch does not
authenticate real users. Session signing requires at least 32 bytes of secret material.

Tenant-owned database records carry an explicit `firm_id`. API queries scope clients to their firm
and auditors to assigned engagements. Run `uv run alembic check` after model changes to confirm a
migration is present.

Conditional checklist items are exposed as yes/no questions at
`GET /engagements/{id}/questionnaire`. A firm answer of “no” hides the item from the client
checklist and creates a pending N/A review for the assigned auditor. Only that auditor can approve
or reject it; rejection restores the requested item without exposing an audit finding.

### Client portal

```bash
cd web
cp .env.example .env.local     # calls the local API by default
npm ci
npm run dev                    # http://localhost:3000
npm run lint
npm run typecheck
npm run build
```

The portal uses real backend sessions and API data by default. Set
`NEXT_PUBLIC_USE_MOCKS=true` only for the built-in synthetic client demo. Client users get the
overview, document checklist, and firm questionnaire; auditor accounts are routed to an internal
review queue where Quinton can inspect evidence, decide N/A requests, review cited findings, and
generate unsigned DOCX/PDF drafts. Browser-visible `NEXT_PUBLIC_*` values must never contain
secrets. See `web/README.md` for the portal-specific workflow.

## Connect to Egnyte

1. In Egnyte's admin console (Apps & Integrations), create an Internal app and note its **Client ID** and **Client Secret**.
2. In `.env` set:
   - `EGNYTE_DOMAIN`: subdomain only, e.g. `quintonsfirm` (for quintonsfirm.egnyte.com)
   - `EGNYTE_API_KEY`: the **Client ID**
   - `EGNYTE_CLIENT_SECRET`: the **Client Secret**
   - `EGNYTE_USERNAME` / `EGNYTE_PASSWORD`: the Egnyte user the app acts as
   - `EGNYTE_SCOPES`: defaults to `Egnyte.filesystem Egnyte.webhooks`
   - `EGNYTE_DEV_ROOT`: `/Shared/AINS-Dev` (the client refuses any path outside it)
3. Test the connection:
   ```bash
   uv run python -m app.egnyte_client whoami
   uv run python -m app.egnyte_client ls /Shared/AINS-Dev
   ```
   Other commands: `mkdir <path>`, `upload <local> <remote>`, `download <remote> <dest>`.

**Tokens.** Egnyte access tokens last **30 days** and are revoked if the user changes their password. Internal apps may request only **10 tokens per user per hour**, and API calls are limited to 2/sec and 1,000/day per token, so reuse tokens rather than logging in on every run:
```bash
uv run python -m app.egnyte_client get-token /tmp/egnyte-token.env
```
This logs in once and writes `EGNYTE_ACCESS_TOKEN` and `EGNYTE_REFRESH_TOKEN` to that file only (mode 600; nothing is printed). Copy the two lines into `.env` and delete the file. With `EGNYTE_ACCESS_TOKEN` set, the password flow is skipped (username/password become optional); on a 401 or expiry the client renews the token with `EGNYTE_REFRESH_TOKEN` (needs `EGNYTE_CLIENT_SECRET`), falling back to the password flow if credentials are set.

Uploads use Egnyte's simple upload endpoint (files up to 100 MB). The client sends the raw file
body as `application/octet-stream`, as required by that endpoint, with Egnyte's SHA-512 integrity
header. Portal ingestion also validates the filename, size, file signature, and the checklist
item's accepted extensions, computes SHA-256, creates the guarded firm/engagement/item hierarchy,
and stores the resulting Egnyte path and version in Postgres.

## Automatic document checks

Successful uploads enqueue a durable Postgres `check_job`; API restarts do not lose work. The
worker runs readability, page-count, review-period, and signature checks before any AI call. Files
that indicate SAR content are routed to the human-only lane and never sent to an AI provider.

Set `AI_PROVIDER=anthropic` or `AI_PROVIDER=openai`. Both adapters require strict structured JSON,
and every draft finding must include a page citation. Findings remain internal for Quinton's
review; clients receive only neutral document-handling reasons such as unreadable, wrong period,
wrong document, or missing pages. Each check and total processing time is recorded, and a five
minute timeout is enforced per file.

## Auditor review and draft reports

Auditors use `GET /auditor/queue` to see only their assigned engagements, including evidence,
check timings, draft findings, and page citations. `PATCH /auditor/findings/{id}` accepts, edits,
or rejects a finding; accepted and edited findings cannot be saved without a page citation.

`POST /auditor/engagements/{id}/report?format=docx|pdf` generates an unsigned draft containing
only auditor-approved findings. The swappable layout and required draft language live in
`templates/report/default.json`. The application never marks a report signed—Quinton reviews and
signs the final report outside this draft-generation step.

## Synthetic evaluations

`data/synthetic/manifest.json` covers clean, missing, wrong-period, unreadable-scan, partial,
planted-SAR, and prompt-injection cases. `uv run python scripts/evaluate_synthetic.py` runs the
credential-free baseline and scores both the client status and whether an AI call was allowed.
The SAR case must never call a provider. Optional `--provider anthropic` and `--provider openai`
modes send only this synthetic set and read credentials from process environment variables, never
from `.env`.

The Cloudflare synthetic demo supports Client view and Auditor view, including the authoritative
request list and engagement setup. Demo actions run in browser memory, reset on refresh, and
never grant a backend session. `cd web && npm run test:e2e` verifies the role switch and core
demonstration interactions; install Playwright Chromium first with `npx playwright install chromium`.

## Data rules (non-negotiable)

1. **No secrets in git.** `.env` and keys live only locally and in the password manager. Never paste them into chats, issues, or AI tools.
2. **Development touches Egnyte only under `/Shared/AINS-Dev`.** The client enforces this with a path guard.
3. **Synthetic data only** in tests, fixtures, and `data/synthetic/`. Real client documents never go in this repo.
4. **SAR material never goes to any AI model.** SAR or SAR-indicating files are routed to a human-only lane.
5. **Intake feedback never reveals audit findings.** Clients may hear "unreadable" or "wrong period", never "your manual is missing X".
6. **Every AI-produced finding cites its source** (document and page).
7. **Humans decide.** Quinton approves, edits, or rejects every finding and signs the report.
