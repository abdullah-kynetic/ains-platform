# Security

## Assets and trust boundaries

- **Protected data:** Client-uploaded AML evidence, identity/email, password hashes, session state, MFA secrets/recovery-code hashes, firm and engagement metadata, questionnaire responses, auditor notes/findings, draft reports, and audit logs.
- **Trusted/untrusted inputs:** Authenticated client/auditor requests, invitation/reset tokens, file names/content/type/size, tenant hostnames, browser input, environment configuration, object-storage/email provider responses. Treat all uploaded content and external error text as untrusted.
- **Threats relevant to this product:** Cross-firm disclosure or write, access to unassigned engagements, role escalation, credential/token theft or replay, malicious/oversized uploads, path/key confusion, audit-log tampering, client disclosure of internal findings, accidental secret exposure, and processing restricted SAR material through an external model.
- FastAPI owns data access. Browser state and route guards are usability controls only. PostgreSQL has no RLS-based tenant policy in the checked-in models; every query/API must enforce ownership and auditor assignment.

## Authentication and authorization

- **Identity/session:** App-owned invite-based email/password auth. Passwords are hashed using `pwdlib` Argon2 support. A signed session token is carried in `ains_session` cookie and backed by `auth_sessions`; revocation/expiry checked server-side. Cookie security is controlled by `SESSION_COOKIE_SECURE`; require secure cookies in deployed HTTPS environments. Public signup is not implemented.
- **MFA:** TOTP is available for auditors; login first accepts credentials and requests a code on a second screen only when enrolled. Recovery codes are hashed, single-use, and revocable. Enrollment has an expiry. Client MFA enforcement is not asserted.
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
| MFA enrollment/recovery management | Denied/not applicable | Authenticated auditor; valid current code required for sensitive rotation |

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
- **Logging redaction:** Never log passwords, session/token values, MFA secrets/recovery codes, uploaded document bytes/content, provider bearer tokens, or full sensitive request payloads. Email code explicitly avoids provider body/token logging. Audit events should contain minimal metadata, not copied document content.

## Dependencies and deployment

- **Dependency review/update:** Python dependencies in `pyproject.toml`/`uv.lock`; web dependencies in `web/package.json`/`package-lock.json`. Review security impact and lockfile changes; no automated dependency update policy documented.
- **Environment separation:** Local, synthetic preview/demo, and live API must remain distinct. `NEXT_PUBLIC_USE_MOCKS=true` is synthetic UI mode and does not establish production auth/storage. Exact deployed project separation, credentials, and endpoints remain unverified. Repo infra describes AWS; owner-provided runtime context describes OVH/Cloudflare; resolve before operations changes.
- **Sensitive review:** Require review of authorization, file handling, auth/session, audit chain, and secret/config changes. No formal security owner/process is documented.

## Verification

See [TESTING.md](TESTING.md) for permission-denial, firm-isolation, malformed/oversized upload, token/MFA, and secret exposure coverage. Residual risks include lack of confirmed malware scanning, operational retention/backup controls, broad non-auth rate limiting, and external audit-chain checkpointing. Owners and due dates: unresolved. This document does not establish regulatory compliance or a security certification.

## Invoice access

All `/auditor/invoices` endpoints require the auditor role. Invoice reads and mutations
require the issuer scope and a current matching engagement assignment to an auditor
in the issuing firm; firm-only invoices require a matching client-firm assignment.
Invoice reads, edits, transitions and numbering are shared within the auditor firm. Unbound legacy auditors receive an individual issuer scope. Client-side route
and sidebar gates supplement server checks. Invoice audit entries belong to the issuer
firm (or system chain for an unbound auditor), so billed clients cannot read invoice
notes or amounts through their activity endpoints. Concurrent mutations lock the invoice
row to avoid duplicate/over payments. No email, model or payment-provider call is made.
