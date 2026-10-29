# Tech stack, systems and vendors

> **Branch status (checked 29 Oct 2026):** `main` is at merge `12f6f70` (PR #52), Alembic head `a111`. PRs **#53–#60 are NOT merged into `main`**; they are a stack (#53 → #54 → #55 → #56 → #57 → #58 → #59 → #60) on top of `main` and are visible only on preview (preview.kiensolutions.com; #59 on layout.kiensolutions.com). Anything tagged **Preview (#NN)** below is not in a fresh `main` checkout. The shared OVH backend already runs the stacked code (`02c480c`, DB at `a115`), so the API serves these routes even though `main` does not contain them.

## Frontend
- **Next.js 16.4.2**, **React 19.3**, TypeScript, **Tailwind CSS v4**, App Router.
- UI: shadcn-style primitives in `web/src/components/ui/` (button, card, dialog, tabs, table, badge…), `lucide-react` icons, `sonner` toasts, `class-variance-authority`, `tailwind-merge`, `clsx`.
- Hosting: **Cloudflare Workers** via `@opennextjs/cloudflare` + `wrangler`.
- Monitoring: `@sentry/browser` (optional).
- Tests: Playwright + `@axe-core/playwright`, Node test runner for unit tests, ESLint, Prettier.

## Backend
- **Python 3.12**, **FastAPI**, Pydantic v2, pydantic-settings, SQLAlchemy 2, Alembic, psycopg 3, uvicorn.
- Auth libs: `pwdlib[argon2]` (passwords), `pyjwt`, `pyotp` (TOTP MFA).
- Reports: `python-docx`, `reportlab`. Storage: `boto3` (S3 API). HTTP: `httpx`, `tenacity`. `sentry-sdk[fastapi]` (optional).
- Package manager: **uv**. Lint: **ruff**. Tests: **pytest** (+ moto, respx).
- Runs in **Docker** (`python:3.12-slim`, non-root user, entrypoint runs `alembic upgrade head` on start) behind **Caddy** (HTTPS).

## Data
- **PostgreSQL 16**, Alembic head on `main` is `a111_unassigned_documents`; the preview stack (#53–#60) adds `a112`–`a115` (head `a115_user_onboarding`), and the shared production DB is already at `a115`. Local dev via `docker compose up -d`.
- Files: **Cloudflare R2** bucket `kien-dev-documents` through the S3 API (`STORAGE_BACKEND=s3`). Egnyte optional and off.

## Environments
| Name | Address | Runs | Notes |
| --- | --- | --- | --- |
| Live | live.kiensolutions.com | Worker `kien-demo-live` | `main` branch (up to PR #52). Only after Abdullah approves visuals |
| Preview | preview.kiensolutions.com | Worker `kien-signin-preview` (version `7e79cfa4`) | Stacked, unmerged PRs #53–#58, #60. Config `web/wrangler.preview.jsonc` (exists only on the stack) |
| Layout | layout.kiensolutions.com | Worker `kien-shadcn-preview` (version `8142b130`) | Unmerged #59 shadcn layout + #60. Config `web/wrangler.layout.jsonc` (exists only on the stack) |
| Design | design.kiensolutions.com | Worker `kien-design-preview` | #50 design exploration, unapproved |
| Firm portals | `<slug>.kiensolutions.com` | Portal Worker | Tenant from host |
| API | api.kiensolutions.com | FastAPI on OVH `/opt/kien` | Shared by all Workers (inferred) |
| Local | localhost:3000 / :8000 | dev servers | Synthetic data |
Note: `web/wrangler.jsonc` names the Worker `ains-platform-demo`; how `kien-demo-live` is bound is **unverified** from the repo (likely deployed with a name override).

## Vendors and services
| Vendor | Used for | Status |
| --- | --- | --- |
| Cloudflare | Workers (frontend), R2 (files), DNS | Active |
| OVH | VPS hosting API + DB (shared with n8n, Twenty, client portal) | Active |
| Resend | Transactional email (invites, resets, magic links). Senders no-reply@ / invite@kiensolutions.com (owner-supplied) | Active |
| GitHub | Repo `abdullah-kynetic/ains-platform`, CI (GitHub Actions, Ubuntu 24.04) | Active |
| Sentry | Error monitoring, free plan, scrubbed | Optional (enabled state unverified) |
| Egnyte | Alternative document store | Off |
| AWS | Account `095384893776` (reinstated 27 Oct 2026), target us-east-1 | Migration planned; Terraform in `infra/aws` |
| OpenAI Codex CLI | Main coding agent (`gpt-6.1-sol`, high effort) | Active |
| Claude Code | Orchestrator project for parallel threads | Being set up |
| Notion | Knowledge base and planning | Active |
| Impeccable (pbakaus/impeccable, Apache 2.0) | Design-quality skill vendored in repo | Installed on `feat/shadcn-layout` (#59, not on `main`) |
| Kiranism next-shadcn-dashboard-starter (MIT) | Layout geometry reference | Credited in THIRD_PARTY_NOTICES.md |
| Supabase | — | Explicitly **not** planned |
| n8n | — | Not used by Kien (shared server only) |

## Environment variable names (never values)
Backend: `DATABASE_URL`, `SESSION_SECRET`, `SESSION_COOKIE_SECURE`, `CORS_ORIGINS`, `PORTAL_URL`, `STORAGE_BACKEND`, `AWS_REGION`, `S3_BUCKET`, `S3_KMS_KEY_ID`, `S3_SSE`, `S3_RETENTION_DAYS`, `S3_RETENTION_MODE`, `RESEND_API_KEY`, `EMAIL_FROM`, `INVITE_EMAIL_FROM`, `AUDITOR_MFA_ISSUER`, `AUDITOR_MFA_ENROLLMENT_TTL_MINUTES`, `CLIENT_INVITATION_TTL_HOURS`, `INVITATION_PREVIEW_ENABLED`, `PASSWORD_RESET_TTL_MINUTES`, `SENTRY_DSN`, `SENTRY_ENVIRONMENT`, `SENTRY_TRACES_SAMPLE_RATE`, `EGNYTE_*`.
Frontend (public, no secrets): `NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_USE_MOCKS`, `NEXT_PUBLIC_MAX_UPLOAD_MB`, `NEXT_PUBLIC_SENTRY_DSN`.
R2 credentials are supplied via deployment config on OVH (exact variable names for R2 endpoint/keys **unverified** from `.env.example`).
