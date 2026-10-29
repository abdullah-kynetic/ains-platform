# Data model

> **Branch status (checked 29 Oct 2026):** `main` is at merge `12f6f70` (PR #52), Alembic head `a111`. PRs **#53–#60 are NOT merged into `main`**; they are a stack (#53 → #54 → #55 → #56 → #57 → #58 → #59 → #60) on top of `main` and are visible only on preview (preview.kiensolutions.com; #59 on layout.kiensolutions.com). Anything tagged **Preview (#NN)** below is not in a fresh `main` checkout. The shared OVH backend already runs the stacked code (`02c480c`, DB at `a115`), so the API serves these routes even though `main` does not contain them.

PostgreSQL 16, SQLAlchemy 2 models in `app/database/models.py`, Alembic migrations in `migrations/versions/`. IDs are UUID strings; timestamps are timezone-aware UTC. **Tenant = firm.** Isolation is by `firm_id` filters and auditor assignment in code (no database RLS).

## Tables (21 with the preview stack; 16 on `main`)
Rows marked *(preview)* exist only after the unmerged migrations `a112`–`a115`.

| Table | Purpose |
| --- | --- |
| `firms` | Tenant (name, unique slug used for `<slug>.kiensolutions.com`) |
| `users` | Clients and auditors: email (unique), role `client`/`auditor`, Argon2 password hash, MFA secret/flag, active flag, firm binding; `onboarding_state` + `onboarding_finished_at` *(preview, a115)* |
| `mfa_recovery_codes` | Hashed one-use auditor recovery codes |
| `client_invitations` | Firm/engagement-scoped invites (hashed token, expiry, accepted/revoked) |
| `engagements` | One test for a firm: review period, due date, status, checklist snapshot, assigned `auditor_id` |
| `checklist_item_instances` | The 34 items per engagement: status, restricted, applicability, N/A state (`na_review_state`, `na_approved_by_id`; `na_previous_state` for undo and the "who marked it" meaning are *(preview, a113/#58)*), decisions, internal notes, follow-up |
| `documents` | Uploaded file metadata: storage key (column still named `egnyte_path`), SHA-256, size, version, uploader, feedback code |
| `check_results` | Receipt/integrity check outcomes |
| `check_jobs` | Durable worker queue (one per document) |
| `finding_drafts` | Human-reviewed draft findings (pending/accepted/edited/rejected) with citations |
| `auditor_tasks` | Auditor to-dos (priority, due, completed) |
| `audit_logs` | SHA-256 hash-chained events per firm (system chain for auth). DB triggers block UPDATE/DELETE/TRUNCATE |
| `auth_sessions` | Server-side sessions (revocable) |
| `magic_link_tokens`, `password_reset_tokens` | Hashed, expiring, single-use tokens |
| `auth_rate_limits` | Sign-in throttling counters |
| `invoice_issuers` | Invoice numbering owner (auditor firm or legacy auditor) *(preview)* |
| `invoices` | Status draft/sent/paid/void, dates, currency, integer cents totals *(preview)* |
| `invoice_line_items` | Lines (Numeric qty, integer cents) *(preview)* |
| `invoice_events` | Append-only invoice history (sent, payment, void) *(preview)* |
| `engagement_reports` | Editable report: status, version (optimistic lock), content, server snapshot, finalized_by/at, `content_sha256` *(preview)* |

## Enums
- Engagement status: draft, collecting, testing, auditor_review, report_drafting, awaiting_signature, complete (pipeline maps these to 6 stages).
- Client item status (`app/checklist.ClientStatus`): not_applicable, requested, checking, action_needed_reupload, action_needed_more, with_auditor, accepted_for_testing, restricted_do_not_upload.
- Check job: queued, running, succeeded, failed. Task priority: high, normal, low. Finding review: pending, accepted, edited, rejected.

## Migration chain (oldest → head)
`fb0fcc8fa1bf` initial schema → `0790ed53879f` check jobs → `4da4c66d93e6` questionnaire → `cf989925f35c` accepted doc types → `8ad73a592bc1` checklist snapshot → `a104` client workflow → `a105` manual review → `a106` auditor tasks → `a107` client invitations → `a108` auditor MFA recovery → `a109` password reset → `a110` audit chain → `a111` unassigned documents (**`main` head**) → *preview stack:* `a112` auditor invoices → `a113` checklist N/A → `a114` engagement reports → **`a115` user onboarding (head)**.
(Order of the early hex revisions is inferred from file names; check `down_revision` before relying on it.)

Production DB is at `a115` because the OVH backend was deployed from the unmerged stack (`02c480c`); `main` only reaches `a111` until #53–#60 merge. Migrations are additive; invoice downgrade deliberately refuses to delete financial history.

## Not yet defined
Retention/deletion schedule, backup objectives (RPO/RTO), cleanup of expired tokens/sessions, legal hold. Do not invent these.
