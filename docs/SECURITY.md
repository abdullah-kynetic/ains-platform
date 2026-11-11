# Security

> **Web sign-in status:** web sign-in is restored and calls the secured backend (password with an emailed code, invitations, password reset, lockout messages, sign-out). The synthetic demo (`NEXT_PUBLIC_USE_MOCKS=true`) still opens as a demo user without sign-in. Verified by `web/e2e-live` against a local backend with synthetic users; not deployed. Backend enforces authentication, the emailed code (when email is configured), firm isolation and assignment. Screens and mocked calls are listed in [frontend-inventory.md](frontend-inventory.md).

## Assets and trust boundaries

- **Protected data:** Client-uploaded AML evidence, identity/email, password hashes, session state, emailed-code hashes and remembered-device token hashes, firm and engagement metadata, questionnaire responses, auditor notes/findings, draft reports, and audit logs.
- **Trusted/untrusted inputs:** Authenticated client/auditor requests, invitation/reset tokens, file names/content/type/size, tenant hostnames, browser input, environment configuration, object-storage/email provider responses. Treat all uploaded content and external error text as untrusted.
- **Threats relevant to this product:** Cross-firm disclosure or write, access to unassigned engagements, role escalation, credential/token theft or replay, malicious/oversized uploads, path/key confusion, audit-log tampering, client disclosure of internal findings, accidental secret exposure, and processing restricted SAR material through an external model.
- FastAPI owns data access. Browser state and route guards are usability controls only. PostgreSQL has no RLS-based tenant policy in the checked-in models; every query/API must enforce ownership and auditor assignment.

## Authentication and authorization

- **Identity/session:** App-owned invite-based email/password auth. Passwords are hashed using `pwdlib` Argon2 support. A signed session token is carried in `ains_session` cookie and backed by `auth_sessions`; revocation/expiry checked server-side. Cookie security is controlled by `SESSION_COOKIE_SECURE`; require secure cookies in deployed HTTPS environments. Public signup is not implemented.
- **Second step (emailed code, replaces TOTP):** after email + password, staff and clients get a 6-digit code by email through Resend. Codes are stored only as keyed HMAC hashes, expire in 10 minutes, work once, burn after 5 wrong guesses, and sending is throttled (30 s between sends, 5 per hour per user). A correct code can remember the browser for 30 days with an httpOnly, SameSite=Lax cookie (Secure when `SESSION_COOKIE_SECURE`), bound to the user and firm and stored server-side as a hash. A user can sign out other devices; a partner or admin can revoke a team member's or an assigned client's remembered devices; a password reset forgets them all. Code sent, accepted, failed, device remembered and device revoked are audit-logged (never the code). **Fallback:** with no `RESEND_API_KEY`/`EMAIL_FROM` (or `EMAIL_SIGN_IN_CODES=false`) the step is skipped, sign-in is email + password only, and a warning is logged on every sign-in. That is a weaker setting: do not run production on it. Emailed codes are weaker than an authenticator app (anyone with the mailbox has the second step); this was a product decision.
- **Roles and permissions:**

| Action | Client firm user | Auditor |
| --- | --- | --- |
| Read firm card/checklist/questionnaire/status | Own firm only | Assigned engagement(s) |
| Upload/re-upload evidence | Own authorized engagement; restricted items reject portal evidence | Can upload/organize evidence on assigned engagement where endpoint allows |
| Client-visible intake feedback | Own firm; neutral document issues only | Assigned engagement can manage feedback |
| Internal notes, finding drafts, review decisions, tasks | Denied | Assigned engagement only |
| Engagement/workspace creation, firm switching/invitations | Denied | Auditor-only routes; assignment/role checks apply |
| Audit log and chain verification | Denied | Assigned engagements; firm-wide view requires all engagements assigned |
| Report sign-off | Denied | Explicit assigned auditor action with artifact hash and attestation |
| Sign out other devices | Own account only | Own account only |
| Revoke remembered devices | Denied | Partner/admin, for own practice members and assigned clients only |

- **Ownership/tenant checks:** Server filters tenant-owned records by `firm_id`; auditor routes additionally check assignment. APIs must deny cross-tenant access regardless of caller-controlled IDs or UI state. Firm mismatch in linked records is a service invariant because composite tenant foreign keys are not present.
- **Recovery/revocation:** Invitation, magic-link, and reset tokens are stored hashed and expire/use once according to auth code; sessions can be revoked/expire. Account deactivation/admin lifecycle and comprehensive session revocation on password change require review; do not assume a central admin workflow exists.

## Secrets and configuration

- **Secret/config variable names only:** `DATABASE_URL`, `SESSION_SECRET`, `RESEND_API_KEY`, `S3_BUCKET`, `S3_KMS_KEY_ID`, Egnyte credential names in `.env.example` (`EGNYTE_API_KEY`, `EGNYTE_CLIENT_SECRET`, `EGNYTE_USERNAME`, `EGNYTE_PASSWORD`), `SENTRY_DSN` and `NEXT_PUBLIC_SENTRY_DSN` (public DSN), plus deployment-specific configuration. `NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_USE_MOCKS`, and `NEXT_PUBLIC_MAX_UPLOAD_MB` are public build-time settings and must contain no secrets.
- **Storage/rotation:** Values are injected through environment/deployment configuration. Secret manager, rotation cadence, and named owner are unresolved. Never read, print, log, commit, screenshot, or request secret values. Use `.env.example` only for names/placeholders.
- **Client exposure:** Any `NEXT_PUBLIC_*` value is shipped to browser code. `SESSION_SECRET`, DB URLs/credentials, storage credentials, Resend keys, Egnyte credentials, and private Sentry credentials stay server-side.

## Input and output handling

- **Validation:** Pydantic request models, constrained database fields, explicit enum/workflow rules, path guards, MIME/extension checks, and file byte-size limits. The checked-in app limit is 100 MB/file; the browser setting is also `NEXT_PUBLIC_MAX_UPLOAD_MB` (default 100). Client checks are convenience; backend must enforce limits.
- **Injection/XSS:** FastAPI/SQLAlchemy parameterized queries; React text rendering escapes values by default. Preserve safe framework patterns; do not render untrusted HTML or interpolate SQL/HTML manually.
- **Upload restrictions:** Files are validated, SHA-256 hashed, stored outside PostgreSQL, and represented by firm-scoped metadata. Restricted checklist items reject portal uploads. Egnyte is optional/off by default; Egnyte development is limited to `/Shared/AINS-Dev` through `EgnyteClient`. Malware scanning/quarantine and stronger Office archive validation are not established; document as residual risk, not as present protection.
- **Rate limits/abuse:** `auth_rate_limits` persists authentication throttling state. Egnyte client has its own rate-limit handling. No general API rate-limit middleware/thresholds were found; account lockout policy and endpoint-specific thresholds are unresolved.
- **SAR handling:** SAR item is designated restricted/human-only; ordinary client portal rejects restricted uploads and tells the client not to upload. A separate SAR pre-screen is planned, not implemented, starts without model runs, and SAR material must never be sent to any model. Do not move SAR into general storage or diagnostics without an approved handling design.
- **Audit log:** SHA-256 hash-chained per firm/system log, immutable through ORM mutation guards and PostgreSQL triggers against UPDATE/DELETE/TRUNCATE. Appends occur with business transaction; no forwarded IP header trusted. This detects ordinary tampering but a privileged administrator able to disable protection and rewrite the full chain can defeat it; external checkpointing is absent.

## Privacy

- **Data collected/purpose:** Email/name for auth and invitations; firm, engagement, checklist/questionnaire state for workflow; uploaded file bytes and hashes for evidence; action/actor/time/IP metadata for audit trail; optional telemetry. Keep telemetry/document contents minimal.
- **Retention, deletion, access:** Unresolved: no approved retention/deletion schedule, legal hold procedure, user export process, or object/database cleanup procedure was found. Do not invent durations. Access is by role, firm, and assignment as above.
- **Logging redaction:** Never log passwords, session/token values, sign-in codes, device tokens, uploaded document bytes/content, provider bearer tokens, or full sensitive request payloads. Email code explicitly avoids provider body/token logging. Audit events should contain minimal metadata, not copied document content.

## Dependencies and deployment

- **Dependency review/update:** Python dependencies in `pyproject.toml`/`uv.lock`; web dependencies in `web/package.json`/`package-lock.json`. Review security impact and lockfile changes; no automated dependency update policy documented.
- **Environment separation:** Local, synthetic preview/demo, and live API must remain distinct. `NEXT_PUBLIC_USE_MOCKS=true` is synthetic UI mode and does not establish production auth/storage. Exact deployed project separation, credentials, and endpoints remain unverified. OVH/Cloudflare is the current owner-supplied target. Checked-in AWS infrastructure is migration preparation; deployed configuration remains unverified.
- **Sensitive review:** Require review of authorization, file handling, auth/session, audit chain, and secret/config changes. No formal security owner/process is documented.

## Verification

See [TESTING.md](TESTING.md) for permission-denial, firm-isolation, malformed/oversized upload, token/emailed-code, and secret exposure coverage. Residual risks include lack of confirmed malware scanning, operational retention/backup controls, broad non-auth rate limiting, and external audit-chain checkpointing. Owners and due dates: unresolved. This document does not establish regulatory compliance or a security certification.

## Invoice access

All `/auditor/invoices` endpoints require the auditor role. Invoice reads and mutations
require the issuer scope and a current matching engagement assignment to an auditor
in the issuing firm; firm-only invoices require a matching client-firm assignment.
Invoice reads, edits, transitions and numbering are shared within the auditor firm. Unbound legacy auditors receive an individual issuer scope. Client-side route
and sidebar gates supplement server checks. Invoice audit entries belong to the issuer
firm (or system chain for an unbound auditor), so billed clients cannot read invoice
notes or amounts through their activity endpoints. Concurrent mutations lock the invoice
row to avoid duplicate/over payments. No email, model or payment-provider call is made.


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

## Auditor client profiles

Client/profile/contact queries require the auditor role and assignment to the client firm's engagement. Profile engagement history is separately filtered by auditor, so another auditor's engagement is omitted even in the same firm. Cross-firm IDs and revoked/unassigned records return 404; clients receive 403. Contact creation accepts only the typed contact fields and always sets `primary=false`; `firm_id` comes from the authorized route. Its audit event contains only IDs, not contact details. UI role switching grants no backend access.
