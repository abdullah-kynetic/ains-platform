# AINS Platform

AINS is an AI-native financial regulatory audit firm. Our software does the legwork; a credentialed auditor (Quinton) makes the calls and signs every report. The first service is the FINRA Rule 3310 independent AML test for broker-dealers; more regulatory audits will follow.

This repo holds the audit engine (Python 3.12, FastAPI, Pydantic) and, later, the client portal (Next.js). Client documents are stored in Egnyte via an Internal API app.

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

## Data rules (non-negotiable)

1. **No secrets in git.** `.env` and keys live only locally and in the password manager. Never paste them into chats, issues, or AI tools.
2. **Development touches Egnyte only under `/Shared/AINS-Dev`.** The client enforces this with a path guard.
3. **Synthetic data only** in tests, fixtures, and `data/synthetic/`. Real client documents never go in this repo.
4. **SAR material never goes to any AI model.** SAR or SAR-indicating files are routed to a human-only lane.
5. **Intake feedback never reveals audit findings.** Clients may hear "unreadable" or "wrong period", never "your manual is missing X".
6. **Every AI-produced finding cites its source** (document and page).
7. **Humans decide.** Quinton approves, edits, or rejects every finding and signs the report.
