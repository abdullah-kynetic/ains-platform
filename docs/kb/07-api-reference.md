# API reference (implemented FastAPI routes)

Routes below are merged source. Deployed routes were not inspected. New mock screen contracts in [frontend inventory](../frontend-inventory.md) are not implemented merely because a similar legacy route exists.

> **Source status (2 Nov 2026):** PRs #53–#60 and #64–#72 are merged in the checked-out history through `d822ce1`. The schema head is `a115_user_onboarding`. Merged source does not establish what is deployed. Runtime state was not inspected. Web sign-in is removed for the synthetic demo; backend auth, MFA and tenant isolation remain required. New screen contracts still use mocks; see [frontend inventory](../frontend-inventory.md).

Base URL: `NEXT_PUBLIC_API_URL` (production api.kiensolutions.com, owner-supplied). Auth by `ains_session` cookie. Errors are FastAPI `{"detail": ...}`.

## Health
- `GET /health`

## Auth (`/auth`)
- `GET /auth/capabilities` · `GET /auth/session` · `POST /auth/password` (sign in) · `POST /auth/sign-out`
- `POST /auth/magic-link` · `POST /auth/magic-link/verify`
- `POST /auth/password-reset/request` · `POST /auth/password-reset/confirm`
- `GET /auth/invitations/{token}` · `POST /auth/invitations/accept`
- `POST /auth/auditor/mfa/enrollment` · `POST /auth/auditor/mfa/enrollment/confirm` · `POST /auth/auditor/mfa/recovery-codes`
- `GET /auth/onboarding` · `POST /auth/onboarding` (finish/skip walkthrough) *(merged, #57/#60)*

## Client engagement
- `GET /engagements/current`
- `POST /engagements/{engagement_id}/documents` (unassigned multi-file upload)
- `POST /engagements/{engagement_id}/items/{item_id}/documents`
- `GET /engagements/{engagement_id}/questionnaire` · `POST .../questionnaire/answers` · `POST .../questionnaire/items/{item_id}/na-review`
- `POST /engagements/{engagement_id}/items/{item_id}/na` (set/undo N/A) *(merged, #55/#58)*
- `POST /engagements/{engagement_id}/items/{item_id}/representations` (sets N/A directly; legacy pending claims remain readable)

## Auditor
- Dashboard/work: `GET /auditor/engagements` · `GET /auditor/engagements/{id}/workspace` · `POST /auditor/engagements/{id}/initialize` · `GET /auditor/queue` · `GET /auditor/pipeline` · `PATCH /auditor/engagements/{id}/pipeline-stage` · `GET /auditor/activity`
- Items: `PATCH /auditor/engagements/{id}/items/{item_id}/decision` · `POST .../items/{item_id}/na` *(merged)* · `POST .../items/{item_id}/feedback` · `POST .../items/{item_id}/follow-up`
- Tasks: `GET /auditor/tasks` · `POST /auditor/engagements/{id}/tasks` · `PATCH /auditor/tasks/{task_id}`
- Workspaces: `POST /auditor/workspaces`
- Invitations: `GET|POST /auditor/engagements/{id}/invitations` · `POST /auditor/invitations/{id}/resend` · `POST /auditor/invitations/{id}/revoke`
- Findings and legacy report: `PATCH /auditor/findings/{finding_id}` · `POST /auditor/engagements/{id}/report` · `POST /auditor/engagements/{id}/report/signoff`
- Editable reports *(merged, #56)*: `GET|POST /auditor/reports` · `GET|PATCH /auditor/reports/{id}` · `POST /auditor/reports/{id}/finalize` · `POST /auditor/reports/{id}/reopen`
- Invoices *(merged, #53/#54)*: `GET /auditor/invoices` (filters status, client, since, until, limit ≤200, offset) · `GET /auditor/invoices/options` · `POST /auditor/invoices` · `GET|PATCH /auditor/invoices/{id}` · `POST /auditor/invoices/{id}/sent|paid|void`
- Audit log: `GET /auditor/audit-log` · `GET /auditor/audit-log/verify-chain`

## Gap found
The frontend maps a `/tenant/branding` response (`web/src/lib/tenant.ts`), and ARCHITECTURE.md lists `/tenant/branding`, but no backend route with that path was found in `app/`. Firm branding may fall back to the default Kien mark in real mode. **Unverified — check before relying on per-firm branding.**
