# Authentication deployment checklist

The public Cloudflare deployment is a synthetic demonstration. Its role switch is disabled when
`NEXT_PUBLIC_USE_MOCKS=false` and does not issue a backend cookie or authenticate a real user.

## Existing backend

- Invite-only database accounts, Argon2 passwords, expiring signed HTTP-only sessions, revocation,
  and mandatory TOTP for auditor sign-in.
- Tenant and assigned-auditor authorization on protected APIs.
- Public `/auth/capabilities` reports available methods without disclosing any credential.
- Magic-link sign-in stays unavailable until an email adapter is configured; it must never
  claim an email was delivered through the default no-op adapter.

## Required to turn on real sign-in

1. Provision persistent hosting for FastAPI, Postgres, and the worker. Cloudflare currently hosts
   the Next.js demonstration only. Choose the backend host before configuring callback URLs.
2. Generate a random `SESSION_SECRET` of at least 32 bytes and store it in the backend host's
   secret manager. Do not paste it into chat or a repository file. Configure `DATABASE_URL` there.
3. Use HTTPS and `SESSION_COOKIE_SECURE=true`. Prefer a same-site application/API arrangement;
   verify cookie behavior and CORS against the actual domains before deployment. Do not weaken
   cookie settings merely to make cross-site development work.
4. Apply migrations. Complete the operator bootstrap and secure invitation/MFA-enrollment flows
   before attempting to create real auditor accounts. Recovery and user deactivation still need
   acceptance testing.
5. Choose and configure an approved email delivery provider if magic links or invitation emails
   are required. Configure delivery privately; never return tokens in API responses or logs.
6. Deploy the authenticated frontend separately from the public demo, set
   `NEXT_PUBLIC_USE_MOCKS=false`, and point `NEXT_PUBLIC_API_URL` to the deployed backend.
7. Test client/auditor sign-in, MFA failures, session expiry, revocation, tenant isolation,
   invitations, recovery, and browser cookie behavior before using real engagement data.

The demo is not the production authentication deployment. Changing an environment toggle alone
does not complete hosting, invitations, MFA enrollment, or operational recovery.
