# AINS Platform

AINS is an AI-native financial regulatory audit firm. Our software does the legwork; a credentialed auditor (Quinton) makes the calls and signs every report. The first service is the FINRA Rule 3310 independent AML test for broker-dealers; more regulatory audits will follow.

This repo holds the audit engine (Python 3.12, FastAPI, Pydantic) and the client portal
(Next.js 16 in `web/`). Client documents are stored in Egnyte via an Internal API app.

## Canonical checklist

`data/checklist/aml_bd_v1.yaml` is the only maintained request inventory: all 34 stable
IDs, client descriptions, applicability questions, and allowed file types. Backend views
read it directly; the web build generates an ignored JSON bundle from it (`npm run catalog`).
Do not hand-maintain a second request list. Rubric fields are intentionally empty for
Quinton to complete; file acceptance is not an audit conclusion. Restricted requests
have no portal evidence types. `initialize_engagement` creates workflow instances from
the catalog; existing noncanonical instance keys require an explicit migration before use.

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

## Storage receipt verification

Successful uploads enqueue a durable Postgres `check_job`. The worker verifies that stored bytes
match the recorded SHA-256 fingerprint and routes the receipt to the auditor. It never analyzes
document contents, calls a model, creates findings, or decides sufficiency. Retries and durations
are recorded. A separate pipeline may connect later through an authenticated backend adapter.

## Auditor review and draft reports

Auditors use `GET /auditor/queue` to see only their assigned engagements, including evidence,
check timings, draft findings, and page citations. `PATCH /auditor/findings/{id}` accepts, edits,
or rejects a finding; accepted and edited findings cannot be saved without a page citation.

`POST /auditor/engagements/{id}/report?format=docx|pdf` generates an unsigned draft containing
only auditor-approved findings. The swappable layout and required draft language live in
`templates/report/default.json`. The application never marks a report signed—Quinton reviews and
signs the final report outside this draft-generation step.

## Synthetic evaluations

`uv run python scripts/evaluate_synthetic.py` checks six synthetic upload cases without network
calls or credentials. It validates file receipt, type signatures, and fingerprints only. Timing,
completeness, and audit sufficiency remain manual auditor decisions. No model runner or model
credential is part of this application.

## Data rules (non-negotiable)

1. **No secrets in git.** `.env` and keys live only locally and in the password manager. Never paste them into chats, issues, or AI tools.
2. **Development touches Egnyte only under `/Shared/AINS-Dev`.** The client enforces this with a path guard.
3. **Synthetic data only** in tests, fixtures, and `data/synthetic/`. Real client documents never go in this repo.
4. **SAR material never goes to any AI model.** SAR or SAR-indicating files are routed to a human-only lane.
5. **Intake feedback never reveals audit findings.** Clients may hear "unreadable" or "wrong period", never "your manual is missing X".
6. **Every AI-produced finding cites its source** (document and page).
7. **Humans decide.** Quinton approves, edits, or rejects every finding and signs the report.
