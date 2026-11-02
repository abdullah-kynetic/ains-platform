# Authentication and permissions

> **Source status (2 Nov 2026):** PRs #53–#60 and #64–#72 are merged in the checked-out history through `d822ce1`. The schema head is `a115_user_onboarding`. Merged source does not establish what is deployed. Runtime state was not inspected. Web sign-in is removed for the synthetic demo; backend auth, MFA and tenant isolation remain required. New screen contracts still use mocks; see [frontend inventory](../frontend-inventory.md).

## Backend authentication and target web flows

Web sign-in, setup, invitation acceptance, reset, sign-out and MFA controls are removed for the demo phase. Restore these before any live deployment or real data. The server rules below remain implemented.

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
| Mark item N/A / undo | **Yes, directly** *(merged #55/#58)* | **Yes** (sees who marked it) *(merged)* | Denied |
| Neutral document feedback | Sees it | Writes it | Denied |
| Internal notes, finding drafts, decisions, tasks | Never | Yes | Denied |
| Reports (edit, finalize, reopen, print) *(legacy editor, merged #56)* | 403, no navigation | Yes | 404 |
| Invoices *(auditor ledger, merged #53/#54)* | No access | Yes, shared within issuing auditor firm | Denied |
| Audit log | Denied | Assigned engagements (firm-wide needs all engagements assigned) | Denied |
| Create workspaces, invite clients | Denied | Yes | — |

**Rule set by Abdullah (Oct 2026):** clients mark N/A themselves because that is how firms run the process now. The assigned auditor has full, unrestricted access to their own client's workspace. Open decision: a client can currently undo an N/A the auditor set (recommended: keep).

## Enforcement
Every tenant-owned query filters by `firm_id`; auditor routes check engagement assignment. Every new API path must have a cross-tenant denial test. UI gates are convenience only.

## Demo logins
The current browser demo selects synthetic roles without sign-in. Backend seeds also define two synthetic identities (one client, one auditor). Credentials are **never** in chat or docs — Abdullah gets them by opening the logins file on his Mac. `python -m app.onboarding_seed --reset-demo` (merged #57) resets only those two demo walkthroughs.
