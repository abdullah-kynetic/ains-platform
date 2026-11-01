# API reference (FastAPI, from route decorators on `fix/onboarding-once`)

Routes marked *(preview)* are not on `main`; they come from unmerged PRs #53–#60 but are served by the shared production API.

> **Branch status (checked 29 Oct 2026):** `main` is at merge `12f6f70` (PR #52), Alembic head `a111`. PRs **#53–#60 are NOT merged into `main`**; they are a stack (#53 → #54 → #55 → #56 → #57 → #58 → #59 → #60) on top of `main` and are visible only on preview (preview.kiensolutions.com; #59 on layout.kiensolutions.com). Anything tagged **Preview (#NN)** below is not in a fresh `main` checkout. The shared OVH backend already runs the stacked code (`02c480c`, DB at `a115`), so the API serves these routes even though `main` does not contain them.

Base URL: `NEXT_PUBLIC_API_URL` (production api.kiensolutions.com, owner-supplied). Auth by `ains_session` cookie. Errors are FastAPI `{"detail": ...}`.

## Health
- `GET /health`

## Auth (`/auth`)
- `GET /auth/capabilities` · `GET /auth/session` · `POST /auth/password` (sign in) · `POST /auth/sign-out`
- `POST /auth/magic-link` · `POST /auth/magic-link/verify`
- `POST /auth/password-reset/request` · `POST /auth/password-reset/confirm`
- `GET /auth/invitations/{token}` · `POST /auth/invitations/accept`
- `POST /auth/auditor/mfa/enrollment` · `POST /auth/auditor/mfa/enrollment/confirm` · `POST /auth/auditor/mfa/recovery-codes`
- `GET /auth/onboarding` · `POST /auth/onboarding` (finish/skip walkthrough) *(preview, #57/#60)*

## Client engagement
- `GET /engagements/current`
- `POST /engagements/{engagement_id}/documents` (unassigned multi-file upload)
- `POST /engagements/{engagement_id}/items/{item_id}/documents`
- `GET /engagements/{engagement_id}/questionnaire` · `POST .../questionnaire/answers` · `POST .../questionnaire/items/{item_id}/na-review`
- `POST /engagements/{engagement_id}/items/{item_id}/na` (set/undo N/A) *(preview, #55/#58)*
- `POST /engagements/{engagement_id}/items/{item_id}/representations` (on `main`: records a client representation for auditor review; on the preview stack it sets N/A)

## Auditor
- Dashboard/work: `GET /auditor/engagements` · `GET /auditor/engagements/{id}/workspace` · `POST /auditor/engagements/{id}/initialize` · `GET /auditor/queue` · `GET /auditor/pipeline` · `PATCH /auditor/engagements/{id}/pipeline-stage` · `GET /auditor/activity`
- Items: `PATCH /auditor/engagements/{id}/items/{item_id}/decision` · `POST .../items/{item_id}/na` *(preview)* · `POST .../items/{item_id}/feedback` · `POST .../items/{item_id}/follow-up`
- Tasks: `GET /auditor/tasks` · `POST /auditor/engagements/{id}/tasks` · `PATCH /auditor/tasks/{task_id}`
- Workspaces: `POST /auditor/workspaces`
- Invitations: `GET|POST /auditor/engagements/{id}/invitations` · `POST /auditor/invitations/{id}/resend` · `POST /auditor/invitations/{id}/revoke`
- Findings and legacy report: `PATCH /auditor/findings/{finding_id}` · `POST /auditor/engagements/{id}/report` · `POST /auditor/engagements/{id}/report/signoff`
- Editable reports *(preview, #56)*: `GET|POST /auditor/reports` · `GET|PATCH /auditor/reports/{id}` · `POST /auditor/reports/{id}/finalize` · `POST /auditor/reports/{id}/reopen`
- Invoices *(preview, #53/#54)*: `GET /auditor/invoices` (filters status, client, since, until, limit ≤200, offset) · `GET /auditor/invoices/options` · `POST /auditor/invoices` · `GET|PATCH /auditor/invoices/{id}` · `POST /auditor/invoices/{id}/sent|paid|void`
- Audit log: `GET /auditor/audit-log` · `GET /auditor/audit-log/verify-chain`

## Gap found
The frontend maps a `/tenant/branding` response (`web/src/lib/tenant.ts`), and ARCHITECTURE.md lists `/tenant/branding`, but no backend route with that path was found in `app/`. Firm branding may fall back to the default Kien mark in real mode. **Unverified — check before relying on per-firm branding.**
