# Authentication and permissions

> **Branch status (checked 29 Oct 2026):** `main` is at merge `12f6f70` (PR #52), Alembic head `a111`. PRs **#53–#60 are NOT merged into `main`**; they are a stack (#53 → #54 → #55 → #56 → #57 → #58 → #59 → #60) on top of `main` and are visible only on preview (preview.kiensolutions.com; #59 on layout.kiensolutions.com). Anything tagged **Preview (#NN)** below is not in a fresh `main` checkout. The shared OVH backend already runs the stacked code (`02c480c`, DB at `a115`), so the API serves these routes even though `main` does not contain them.

## Sign-in
- **Invite only.** No public sign-up. Auditors invite clients to a firm + engagement (`/auditor/engagements/{id}/invitations`); client accepts at `/accept-invitation` and sets a password.
- Email + password (Argon2 hashes). Optional magic link. Password reset by emailed single-use token.
- Session: signed token in the `ains_session` cookie, backed by `auth_sessions` (expiry + revocation checked server-side). `SESSION_COOKIE_SECURE` must be true in HTTPS environments.
- **Auditor MFA:** TOTP (authenticator app). When enrolled, a second screen asks for the code or a one-use recovery code. Client MFA is not enforced.
- Sign-in throttling via `auth_rate_limits`. No general API rate limits yet (planned).
- Emails sent through Resend; if `RESEND_API_KEY` is missing, email endpoints return 503.

## Roles
Two roles only: **client** and **auditor**. No firm-admin. The synthetic demo role switch never grants real access.

## Who can do what
| Action | Client | Auditor (assigned) | Auditor (not assigned) |
| --- | --- | --- | --- |
| See firm card, checklist, questionnaire, progress | Own firm only | Yes, full | Denied (404) |
| Upload / re-upload evidence | Own engagement (not restricted items) | Yes | Denied |
| Mark item N/A / undo | **Yes, directly** *(preview #55/#58; on `main` client proposes, auditor approves)* | **Yes** (sees who marked it) *(preview)* | Denied |
| Neutral document feedback | Sees it | Writes it | Denied |
| Internal notes, finding drafts, decisions, tasks | Never | Yes | Denied |
| Reports (edit, finalize, reopen, print) *(preview #56)* | 403, no navigation | Yes | 404 |
| Invoices *(preview #53/#54)* | No access | Yes, shared within issuing auditor firm | Denied |
| Audit log | Denied | Assigned engagements (firm-wide needs all engagements assigned) | Denied |
| Create workspaces, invite clients | Denied | Yes | — |

**Rule set by Abdullah (Oct 2026):** clients mark N/A themselves because that is how firms run the process now. The assigned auditor has full, unrestricted access to their own client's workspace. Open decision: a client can currently undo an N/A the auditor set (recommended: keep).

## Enforcement
Every tenant-owned query filters by `firm_id`; auditor routes check engagement assignment. Every new API path must have a cross-tenant denial test. UI gates are convenience only.

## Demo logins
Two synthetic demo identities (one client, one auditor). Credentials are **never** in chat or docs — Abdullah gets them by opening the logins file on his Mac. `python -m app.onboarding_seed --reset-demo` (preview stack only, #57) resets only those two demo walkthroughs.
