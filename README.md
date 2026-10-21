# AINS Platform

AINS is an AI-native financial regulatory audit firm. Our software does the legwork; a credentialed auditor (Quinton) makes the calls and signs every report. The first service is the FINRA Rule 3310 independent AML test for broker-dealers; more regulatory audits will follow.

This repo holds the audit engine (Python 3.12, FastAPI, Pydantic) and the client portal
(Next.js 16 in `web/`). Client documents are stored in Egnyte via an Internal API app.

## Authoritative checklist

The [M&A broker-dealer AML request list](docs/checklist/aml-ma-bd-request-list.md) preserves all
34 requests from the user-supplied Word document, with stable reference IDs and source issues
for Quinton to review. Use this reference when implementing the checklist; do not substitute the
portal's synthetic demo items. SAR filings and decision records require controlled human handling.

## Setup

```bash
# 1. Install uv: https://docs.astral.sh/uv/
uv sync                          # creates .venv and installs deps (incl. dev)

# 2. Local Postgres
docker compose up -d

# 3. Environment
cp .env.example .env             # fill in values locally; never commit .env

# 4. Run
uv run uvicorn app.main:app --reload    # http://localhost:8000/health
uv run pytest
uv run ruff check .
```

### Client portal

```bash
cd web
cp .env.example .env.local     # synthetic demo data is enabled by default
npm ci
npm run dev                    # http://localhost:3000
npm run lint
npm run typecheck
npm run build
```

The portal currently uses synthetic mock data when `NEXT_PUBLIC_USE_MOCKS=true`. Browser-visible
`NEXT_PUBLIC_*` values must never contain secrets. See `web/README.md` for the API contract and
portal-specific workflow.

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

Uploads use Egnyte's simple upload endpoint (files up to 100 MB).

## Data rules (non-negotiable)

1. **No secrets in git.** `.env` and keys live only locally and in the password manager. Never paste them into chats, issues, or AI tools.
2. **Development touches Egnyte only under `/Shared/AINS-Dev`.** The client enforces this with a path guard.
3. **Synthetic data only** in tests, fixtures, and `data/synthetic/`. Real client documents never go in this repo.
4. **SAR material never goes to any AI model.** SAR or SAR-indicating files are routed to a human-only lane.
5. **Intake feedback never reveals audit findings.** Clients may hear "unreadable" or "wrong period", never "your manual is missing X".
6. **Every AI-produced finding cites its source** (document and page).
7. **Humans decide.** Quinton approves, edits, or rejects every finding and signs the report.
