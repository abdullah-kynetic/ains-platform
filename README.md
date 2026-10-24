# AINS Platform

AINS is an AI-native financial regulatory audit firm. Our software does the legwork; a credentialed auditor (Quinton) makes the calls and signs every report. The first service is the FINRA Rule 3310 independent AML test for broker-dealers; more regulatory audits will follow.

This repo holds the audit workflow backend (Python 3.12, FastAPI, Pydantic) and the portal
(Next.js 16 in `web/`). Client documents use S3 by default; Egnyte is an optional, off-by-default connector.

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

The backend owns authentication and uses an HTTP-only `ains_session` cookie. There is no public
sign-up endpoint. Assigned auditors create firm-bound client invitations, and clients set a
password while accepting the single-use, expiring token. Invitations can be rotated or revoked;
an email cannot be invited into more than one firm. Client users may later sign in with a password
or magic link. Auditors enroll TOTP MFA with their existing password and receive ten single-use,
hashed recovery codes; replacing recovery codes requires a current authenticator code. Set
`SESSION_SECRET` to a long, random value before using sign-in. Set `RESEND_API_KEY`, `EMAIL_FROM` and `PORTAL_URL` to enable Resend delivery for
magic links, invitations and password reset; unconfigured email returns 503. For synthetic local testing only,
set `INVITATION_PREVIEW_ENABLED=true` to return an acceptance link to the auditor UI; never enable
token previews in a shared or production system.

Tenant-owned database records carry an explicit `firm_id`. API queries scope clients to their firm
and auditors to assigned engagements. Run `uv run alembic check` after model changes to confirm a
migration is present.

Supabase is not part of the planned AINS architecture. FastAPI remains the application,
authentication and authorization boundary, backed by an AINS-managed PostgreSQL deployment; the
browser does not connect directly to the database. The old synthetic hosted-PostgreSQL evaluation
is retained only as an archived decision record in
[`docs/supabase-postgres-poc.md`](docs/supabase-postgres-poc.md). Do not provision or configure
Supabase for this project.

Conditional checklist items are exposed as yes/no questions at
`GET /engagements/{id}/questionnaire`. A “no” answer stays visible as pending auditor review
and disables uploads, rather than silently becoming approved N/A. Where the source requests
a no-activity representation, the client must explicitly confirm it. Auditor approval removes
the request from the active list; rejection restores it. The overview links questionnaire →
applicable requests → central upload. Auditor follow-up releases existing catalog requests;
document feedback accepts only fixed, neutral replacement reasons, never arbitrary findings.

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

The portal uses real backend sessions and API data by default. `NEXT_PUBLIC_API_URL`
is the only API base (`web/src/lib/api.ts`): `http://localhost:8000` for local dev
(`http://localhost:3000`) and `https://api.kiensolutions.com` for production. Set
`NEXT_PUBLIC_USE_MOCKS=true` only for the built-in synthetic client demo. Client users get the
overview, document checklist, and firm questionnaire; auditor accounts are routed to an internal
review queue where Quinton can inspect evidence, decide N/A requests, review cited findings, and
generate unsigned DOCX/PDF drafts. Browser-visible `NEXT_PUBLIC_*` values must never contain
secrets. See `web/README.md` for the portal-specific workflow.

## Storage

S3 is the default (`STORAGE_BACKEND=s3`). Configure `S3_BUCKET` and `AWS_REGION`,
using an instance role in AWS. See [the AWS runbook](docs/deploy-aws.md) for encryption,
retention and deployment. Egnyte credentials are not required.

### Optional Egnyte connector

To opt in, set `STORAGE_BACKEND=egnyte`, then:

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

Credentials and token renewal are handled by the guarded client. Use the CLI
commands above; never print tokens or export them into files.

Uploads use Egnyte's simple upload endpoint (files up to 100 MB). The client sends the raw file
body as `application/octet-stream`, as required by that endpoint, with Egnyte's SHA-512 integrity
header. Portal ingestion also validates the filename, size, file signature, and the checklist
item's accepted extensions, computes SHA-256, creates the guarded firm/engagement/item hierarchy,
and stores the resulting Egnyte path and version in Postgres.

## Storage receipt verification

### Central upload demo

In the synthetic web demo, open `/upload`, search for a request, choose multiple synthetic
files, adjust their destinations, then confirm. Each file gets its own receipt/failure and
SHA-256 fingerprint. Receipt metadata persists in this browser; file bytes are not stored
or sent to storage in demo mode. The real API uses firm-scoped S3 keys by default;
the optional Egnyte connector remains guarded under `/Shared/AINS-Dev`.
Run `cd web && npx playwright install chromium && npm run test:e2e` for the browser test.
The checklist is a progress view, not a second upload screen.

Successful uploads enqueue a durable Postgres `check_job`. The worker verifies that stored bytes
match the recorded SHA-256 fingerprint and routes the receipt to the auditor. It never analyzes
document contents, calls a model, creates findings, or decides sufficiency. Retries and durations
are recorded. A separate pipeline may connect later through an authenticated backend adapter.

## Auditor review and draft reports

`/auditor` lists assigned client engagements; each workspace lists canonical requests,
document versions/fingerprints, and a chronological actor/change history. Applicability
(`applicable` / `not_applicable`) is separate from evidence assessment (`supported`, `partial`,
`conflicting`, `unable_to_determine`). Internal notes and decisions never appear in client APIs.
New uploads, changed answers and follow-up/feedback invalidate old assessments. Readiness
requires all 34 workflow instances and human decisions, no pending representations/storage
receipts or outstanding replacement requests. It means ready for human report drafting,
not a clean audit opinion, completed rubric, or signed report.

For an assigned, empty engagement, `POST /auditor/engagements/{id}/initialize` creates all
34 instances from the YAML. Existing legacy instances are rejected rather than remapped.
The synthetic demo includes an explicitly labeled client/auditor view switch; production
still requires backend authentication, auditor MFA, and engagement assignment.

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
4. **Restricted material stays outside the portal.** Catalog metadata routes human handling; no restricted document contents belong in uploads, notes, fixtures, or repository artifacts.
5. **Intake feedback never reveals audit findings.** Clients may hear "unreadable" or "wrong period", never "your manual is missing X".
6. **No model inference in this repository.** Any future external pipeline needs its own approved authenticated adapter; evidence citations remain required for findings.
7. **Humans decide.** Quinton approves, edits, or rejects every finding and signs the report.

## Build handoff

See `docs/build-handoff.md` for the six-task delivery summary, synthetic demo instructions,
validation and remaining production prerequisites. CI includes browser/accessibility tests and
short-lived synthetic screenshots. Automated accessibility checks are not a compliance certification.

AWS deployment, storage selection, secrets, costs and Cloudflare production builds are documented
in [the deployment runbook](docs/deploy-aws.md).
