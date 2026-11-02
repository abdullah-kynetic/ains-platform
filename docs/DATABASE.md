# Database

## Storage model

- **Database/provider:** PostgreSQL 16. SQLAlchemy 2 models in `app/database/models.py`; Alembic revisions in `migrations/versions/`.
- **Ownership model:** Tenant = firm. Tenant-owned tables carry `firm_id` where applicable, even when reachable through another relationship; client identity is bound to one firm. Auditor access is assignment-based through `engagements.auditor_id`.
- **Data classification:** Internal, personal, and sensitive financial/workflow data. Document bytes may contain highly sensitive client material. SAR content is restricted and must not be uploaded to ordinary portal flow or sent to any model. Exact regulatory classification and retention schedule are unresolved.

## Entities

| Entity/table | Purpose | Owner | Retention |
| --- | --- | --- | --- |
| `firms` | Tenant identity | System | Unresolved |
| `users` | Client/auditor identities, credentials and firm binding | Firm or system auditor | Unresolved |
| `mfa_recovery_codes` | Hashed one-use auditor recovery codes | User | Until used/revoked; cleanup unresolved |
| `client_invitations` | Firm/engagement-scoped invitation lifecycle | Firm | Unresolved |
| `engagements` | Review period, status, checklist snapshot, assigned auditor | Firm | Unresolved |
| `auditor_tasks` | Assigned internal work | Firm/engagement | Unresolved |
| `checklist_item_instances` | Per-engagement checklist and human decisions | Firm/engagement | Unresolved |
| `documents` | Metadata and object-storage locator for uploaded evidence | Firm/engagement | Unresolved |
| `check_results` | Receipt/integrity check outcomes | Firm/document | Unresolved |
| `finding_drafts` | Human-reviewed finding drafts | Firm/engagement | Unresolved |
| `check_jobs` | Durable document receipt-check queue | Firm/document | Unresolved |
| `audit_logs` | Hash-chained activity events | Firm or system | Unresolved |
| `auth_sessions` | Persisted session revocation/expiry | User | Expired-row cleanup unresolved |
| `magic_link_tokens` | Hashed, expiring sign-in tokens | User | Unresolved cleanup |
| `password_reset_tokens` | Hashed, expiring password recovery tokens | User | Unresolved cleanup |
| `auth_rate_limits` | Authentication rate-limit counters/windows | System/key | Unresolved cleanup |

## Schema

Types below follow SQLAlchemy declarations and PostgreSQL storage semantics. Unless called out, IDs are `String(36)` UUID strings with Python `new_id()` defaults; timestamps are timezone-aware `DateTime` with Python UTC defaults; nullable fields are marked `?`; JSON is SQLAlchemy `JSON`; enums are non-native string enums. No implicit `ON DELETE CASCADE` is declared on foreign keys. ORM delete-orphan cascades apply only to engagement items, item documents, document check results/check job.

- **`firms`** — `id String(36)` PK; `name String(255)` required; `slug String(100)` required, unique/indexed; `created_at DateTime(tz)` required/default UTC.
- **`users`** — `id String(36)` PK; `firm_id String(36)?` FK firms/index; `email String(320)` required, globally unique/indexed (also composite unique `(firm_id,email)`); `name String(255)` required; `role Enum(UserRole: client|auditor)` required/index; `password_hash String(255)?`; `mfa_secret String(64)?`; `mfa_enabled Boolean` default false; `mfa_enrollment_expires_at DateTime(tz)?`; `is_active Boolean` default true; `invited_at DateTime(tz)` default UTC; `accepted_at DateTime(tz)?`; `created_at DateTime(tz)` default UTC.
- **`mfa_recovery_codes`** — `id String(36)` PK; `user_id String(36)` FK users/index; `code_hash String(64)` required unique/index; `used_at DateTime(tz)?`; `revoked_at DateTime(tz)?`; `created_at DateTime(tz)` default UTC; composite index `(user_id,used_at,revoked_at)`.
- **`client_invitations`** — `id String(36)` PK; `firm_id String(36)` FK firms/index; `engagement_id String(36)` FK engagements/index; `email String(320)` index; `name String(255)`; `token_hash String(64)` unique/index; `expires_at DateTime(tz)` index; `created_by_id String(36)` FK users/index; `accepted_user_id String(36)?` FK users, unique; `accepted_at DateTime(tz)?`; `revoked_at DateTime(tz)?`; `created_at DateTime(tz)` default UTC; `updated_at DateTime(tz)` default/on update UTC; unique email; composite index `(firm_id,engagement_id)`.
- **`engagements`** — `id String(36)` PK; `firm_id String(36)` FK firms/index; `auditor_id String(36)?` FK users/index; `engagement_type String(255)` default FINRA Rule 3310 Independent AML Test; `status Enum(EngagementStatus)` default collecting; `checklist_version String(120)?`; `checklist_snapshot JSON?`; `review_period_start Date` required; `review_period_end Date` required; `due_date Date?`; `created_at`, `updated_at DateTime(tz)` default UTC; CHECK `review_period_end >= review_period_start`; index `(firm_id,status)`.
- **`auditor_tasks`** — `id String(36)` PK; `firm_id String(36)` FK firms/index; `engagement_id String(36)` FK engagements/index; `assignee_id String(36)` FK users/index; `title String(255)`; `request_id String(120)?`; `due_date Date?`; `priority Enum(TaskPriority: high|normal|low)` default normal; `completed_at DateTime(tz)?`; `completed_by_id String(36)?` FK users; `created_at`, `updated_at DateTime(tz)` default UTC; indexes `(firm_id,engagement_id)`, `(assignee_id,completed_at)`.
- **`checklist_item_instances`** — `id String(36)` PK; `firm_id String(36)` FK firms/index; `engagement_id String(36)` FK engagements/index; `item_key`, `section_key String(120)`; `section_title`, `title String(255)`; `description Text` default empty; `accepted_extensions JSON` default list; `review_period_rule String(255)?`; `min_pages Integer` default 1; `requires_signature Boolean` default false; `position Integer` default 0; `status Enum(ClientStatus)` default requested; `client_reason Text?`; `restricted`, `is_conditional Boolean` default false; `condition_question Text?`; `applicable Boolean` default true; `applicability_answer Boolean?`; `na_review_state Enum(NAReviewState)?`; `na_requested_at DateTime(tz)?`; `na_approved_by_id String(36)?` FK users; `representation String(50)?`; `follow_up Boolean` default false; `applicability_decision`, `assessment String(30)?`; `internal_notes Text` default empty; timestamps default UTC; unique `(engagement_id,item_key)`; index `(firm_id,engagement_id)`.
- **`documents`** — `id String(36)` PK; `firm_id String(36)` FK firms/index; `engagement_id String(36)?` FK engagements/index; `item_instance_id String(36)?` FK checklist items/index; `uploaded_by_id String(36)` FK users; `original_name String(255)`; `content_type String(255)?`; `size_bytes Integer`; `egnyte_path String(1024)` (legacy name for storage object locator); `sha256 String(64)` index; `version String(255)` default `1`; `feedback_code String(50)?`; `created_at DateTime(tz)` default UTC; unique `(item_instance_id,egnyte_path,version)`; index `(firm_id,item_instance_id)`.
- **`check_results`** — `id String(36)` PK; `firm_id String(36)` FK firms/index; `document_id String(36)` FK documents/index; `check_type String(100)`; `status String(50)`; `client_reason Text?`; `details JSON` default dict; `citations JSON` default list; `duration_ms Integer?`; `created_at DateTime(tz)` default UTC; index `(firm_id,document_id)`.
- **`finding_drafts`** — `id String(36)` PK; `firm_id String(36)` FK firms/index; `engagement_id String(36)` FK engagements/index; `document_id String(36)?` FK documents/index; `title String(255)`; `body Text`; `severity String(50)`; `citations JSON` default list; `review_state Enum(ReviewState)` default pending; `reviewed_by_id String(36)?` FK users; `reviewed_at DateTime(tz)?`; `created_at`, `updated_at DateTime(tz)` default UTC; index `(firm_id,engagement_id)`.
- **`check_jobs`** — `id String(36)` PK; `firm_id String(36)` FK firms/index; `document_id String(36)` FK documents, unique/index; `status Enum(CheckJobStatus)` default queued; `attempts Integer` default 0; `available_at DateTime(tz)` default UTC; `started_at`, `completed_at DateTime(tz)?`; `duration_ms Integer?`; `last_error_code String(120)?`; `created_at DateTime(tz)` default UTC; index `(status,available_at)`.
- **`audit_logs`** — `id String(36)` PK; `firm_id String(36)?` FK firms/index; `actor_id String(36)?` FK users/index; `action`, `entity_type String(120)`; `entity_id String(36)?`; `ip_address String(45)?`; `sequence Integer`; `previous_hash`, `row_hash String(64)`; `details JSON` default dict; `created_at DateTime(tz)` default UTC; index `(firm_id,created_at)`; unique `(firm_id,sequence)`.
- **`auth_sessions`** — `id String(36)` PK; `user_id String(36)` FK users/index; `expires_at DateTime(tz)` index; `revoked_at DateTime(tz)?`; `created_at DateTime(tz)` default UTC.
- **`magic_link_tokens`** — `id String(36)` PK; `user_id String(36)` FK users/index; `token_hash String(64)` unique/index; `expires_at DateTime(tz)` index; `used_at DateTime(tz)?`; `created_at DateTime(tz)` default UTC.
- **`password_reset_tokens`** — `id String(36)` PK; `user_id String(36)` FK users/index; `token_hash String(64)` unique/index; `expires_at DateTime(tz)` index; `used_at DateTime(tz)?`.
- **`auth_rate_limits`** — `key String(64)` PK; `count Integer` default 0; `window_start DateTime(tz)` required.

Application defaults are Python-side unless a migration defines a server default. `updated_at` values are ORM-maintained, not a general database trigger. Migrations are authoritative for installed schema; compare them when changing models.

## Relationships

- Firm has many users and engagements. User may be firm-bound or system-level and may have assigned engagements.
- Engagement belongs to a firm; may have an assigned auditor; has ordered checklist items. ORM cascade deletes its checklist items.
- Checklist item belongs to engagement and firm; has documents. ORM cascade deletes its documents.
- Document belongs to firm and optionally engagement/item; has check results and one check job. ORM cascade deletes those dependent records.
- Auditor task belongs to a firm/engagement and has assignee/completer references. Finding draft belongs to a firm/engagement and optionally document/reviewer.
- Invitations link a firm/engagement, creator, and optional accepted user. Auth tokens/sessions and recovery codes refer to users.
- No broad FK `ON DELETE CASCADE` policy is declared. Explicit retention/deletion and cleanup behavior is unresolved; do not infer that deleting a firm safely removes all associated objects.

## Access rules

- FastAPI is the only application data boundary. Client actions require an authenticated active client bound to the target `firm_id`; only that firm’s assigned engagement and allowed client fields are readable/writable. Client cannot access internal notes, finding drafts, auditor tasks, audit log, or auditor-only decisions.
- Auditor routes require active auditor identity. Reads/writes to engagement-owned records require assignment to that engagement; firm-wide audit-log access requires assignment to every engagement in the firm. UI route gates are not authorization.
- Auth/token tables are accessed only by auth code. Service/worker records jobs and results under their firm/document. Add server-side ownership denial tests for every new endpoint.
- Isolation is enforced through explicit `firm_id` filters and assignment checks, not database RLS. Composite foreign keys do not enforce that a linked record’s firm matches its parent; API/service checks must ensure consistency.

## Queries and indexes

- Engagement lists filter `(firm_id,status)` and auditor assignment; items filter `(firm_id,engagement_id)`; documents filter `(firm_id,item_instance_id)` or `(firm_id,engagement_id)`; findings/tasks filter by firm/engagement; audit logs filter firm and timestamp then sequence; jobs claim queued rows by `(status,available_at)`.
- Model-declared indexes and unique constraints are listed above. Migration-added indexes/triggers must also be reviewed. Pagination/ordering bounds and query performance SLOs are unresolved.

## Migrations and seed data

- **Tool:** Alembic, configured by `migrations/env.py`; revision chain in `migrations/versions/`. Change model and migration together, inspect generated SQL and data/backfill behavior, apply only in authorized environment, and preserve reversible downgrade where safe. Never run production migrations without specific authorization.
- **Seed data:** `app/demo_seed.py`, tests, and `data/synthetic/` are synthetic. Never seed real client data or credentials.
- **Backups/restore:** Unresolved. Repository docs do not define verified backup schedule, retention, encryption, point-in-time recovery, restore objectives, or restore drill evidence. Establish these before production readiness.

## Data validation

Database constraints include review period ordering, unique firm slug, unique email/token hashes, unique checklist key per engagement, unique check job per document, unique document version tuple, and unique audit sequence per firm. Pydantic and service code enforce role-specific allowed values, date/file constraints, firm ownership, assignment, workflow transitions, and restricted checklist behavior. Upload limit is 100 MB per file; supported extensions derive from the checklist and ingestion validation. On mismatch, reject safely and do not expose other tenant existence/content.

## Auditor invoice ledger

Additive revision `a112_auditor_invoices` creates four tables without changing existing
tables or backfilling their data:

- `invoice_issuers`: numbering owner (exactly one of auditor firm or legacy unbound
  auditor), unique owner links and next number. An existing firm/user row lock serializes
  first use and subsequent allocation. Numbers are unique per issuer, increasing and
  retained for void invoices; a rolled-back transaction consumes no number.
- `invoices`: issuer, assigned auditor, client `firm_id`, optional engagement, unique
  issuer/number, draft/sent/paid/void status, issue/due dates, currency, notes, integer
  subtotal/total/amount-paid cents, full-payment date and timestamps.
- `invoice_line_items`: invoice, description, Numeric(12,2) quantity, integer rate/amount
  cents, unique ordered position. Each line rounds half-up to the nearest cent before
  summation. Positive invoice totals are capped at 100,000,000,000 cents.
- `invoice_events`: invoice, type, from/to status, optional integer payment cents,
  recorded timestamp, actor and JSON metadata (including the effective payment date).
  Application routes append events; they do not edit or delete them. These are not the
  immutable chained `audit_logs` table; actions also append to that existing audit ledger.

USD/EUR/GBP/CAD/AUD/CHF are supported with two-decimal minor units. No taxes or currency
conversion. Fully paid and void invoices are terminal; payments must be positive and
cannot exceed the balance. Paid invoices and partially paid invoices cannot be voided.
Invoice migration downgrade intentionally refuses deletion of financial history; image
rollback retains the additive tables. Retention/refund policies remain unresolved.


## Numbered checklist N/A

All 34 catalog requests remain visible with their original numbers; N/A sorts last.
Clients can directly set/undo N/A on their own engagement; its assigned auditor can
also set/undo it. Questionnaire no answers and the legacy representation endpoint
now set N/A directly. Existing pending claims remain readable and reviewable for
compatibility. N/A counts as done; collection still excludes the two restricted items
(32 ordinary requests). Restricted-content handling and upload prohibitions remain.
Undo restores `na_previous_state` (revision `a113_checklist_na`). The existing
`na_approved_by_id` stores the marking actor for both roles; the related user supplies
`naMarkedByRole`. Each toggle records actor ID and role in the immutable audit chain.
No schema migration is needed. This collection declaration is not an audit finding.
Auditor workspace links come from server-authorized assignments rather than a disabled
synthetic client-role switch. Unassigned auditors and other firms remain denied.


## Editable auditor reports

The existing report template, approved finding drafts, legacy DOCX/PDF generator and
hash-attestation sign-off remain in place. `/auditor/reports` adds persisted editing
per assigned engagement in `engagement_reports` (additive `a114_engagement_reports`).
Firm/period/scope and 34 request statuses are snapshotted server-side on create/save.
Approved findings prefill the narrative; auditors enter per-item report findings.
Restricted items allow metadata only. The native rich-text editor accepts text paste;
the server keeps only formatting tags with no attributes, scripts, URLs or embedded content.
Version checks and row locks prevent lost updates. Finalization requires explicit human
attestation, freezes content and records its SHA-256. Audited reopening permits edits;
prior final hashes remain in the immutable audit chain. Final status does not complete
the engagement, deliver a report, establish a clean opinion or create a cryptographic
signature. Clients receive 403 from the auditor editor; unassigned auditors get 404. The separate client Report screen is a synthetic mock pending its backend slice.
Print view uses the invoice-style browser print/save PDF flow. The idempotent
`python -m app.report_seed` seeds one existing explicitly synthetic demo engagement.


## First sign-in walkthrough

`GET/POST /auth/onboarding` reads/finishes only the authenticated user's preference.
Nullable `users.onboarding_state` and `onboarding_finished_at` are added by
`a115_user_onboarding`; null means pending. Completed/skipped states are terminal
through the public endpoint and audited once. Each role has a three-step skippable
modal using the existing dialog, focus handling, tokens and reduced-motion behavior.
The app has auditor/client roles and no distinct firm-admin role; the auditor flow
explains the workspace management auditors already have permission to use.
`python -m app.onboarding_seed --reset-demo` resets only the two exact existing
synthetic demo identities, preserves credentials and records demo reset events.
Demo walkthroughs stay finished after verification; reset only for an explicit demo run.
`UserView` includes nullable `onboarding_state` in sign-in, invitation acceptance and
`GET /auth/session`. Both roles open the tour only for null state, with no extra GET
required. Completing, skipping, Close and Escape save through the same idempotent
POST; the session updates only after a successful save. Failed saves stay visible
with a retryable error. Live mode never uses localStorage for onboarding state.
New users start null; existing pending users are not backfilled. No new migration
is needed beyond `a115`. Static browser mocks have no sign-in;
set `kien-synthetic-onboarding-enabled=1` to exercise their local walkthrough state.

The demo-only `python -m app.monday_seed` preserves the exact demo auditor legacy
ledger while enabling a synthetic issuing firm and colleague-created invoice. It refuses
non-synthetic clients or merging populated ledgers; no credentials are created or changed.
