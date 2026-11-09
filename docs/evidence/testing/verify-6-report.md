# VERIFY-6 report: PR #87 web sign-in restore, claude/impl-4-web-signin @ 120f82111334806ff3bcf2f49d20ac76f73c9eac (based on b6de342; b3b02ac not included)

Environment: sandbox, Python 3.12.3, Node via npm ci, PostgreSQL 16.15 as `postgres`, Playwright Chromium (/opt/pw-browsers/chromium-1243). Synthetic data only. No code fixed.

## Checks
| Check | Result |
|---|---|
| `npm run lint` | PASS |
| `npm run typecheck` | PASS |
| `npm run test:unit` | PASS: 18 tests |
| `npm run test:e2e:live` (real backend scripts/e2e_backend.py, no mocks) | PASS: 8 passed (redirect keeps destination, sign-in, generic wrong-password message, MFA, external next ignored, lockout with wait message and other user unaffected, sign-out, invitation) |
| `npm run test:e2e` (mock build) | 80 passed, 1 failed: tasks.spec.ts:22 (the known date-dependent failure, PR #86) |
| Backend suite excl. PG files | PASS: 341 passed |
| PG files, non-root, PostgreSQL 16.15 | PASS: 11 passed |
| Open redirect, `next` | PASS: own probe of 19 inputs (//, backslash, tab, %2F, /..//, https://, javascript:, ///, control chars, /.//) all end as same-origin relative paths or "/" |
| Auth bypass outside demo build | PASS with note V6-4: AUTH_REMOVED is gone; mock session only when NEXT_PUBLIC_USE_MOCKS=true (build time) and the live-API flag is not set; real build calls /auth/session. Backend remains the authority |
| Session cookie | PASS in code: HttpOnly, SameSite=lax, Max-Age, Path=/. Secure only if SESSION_COOKIE_SECURE (V6-1) |
| Sign-out | PASS: cookie cleared, and replaying the old cookie after sign-out returns 401 |
| MFA | PASS: password then "MFA code required" step; wrong code gives its own message and counts as a failure; recovery codes accepted; unenrolled auditor sent to account setup |
| Invitations single-use | PASS: second accept 410 "already used", details link 410 afterwards |
| Lockout display | PASS: 429 shows "try again in about N minutes" from Retry-After; messages never say which of email/password was wrong |
| CORS Retry-After change | PASS: only `expose_headers=["Retry-After"]` added; evil origin gets no Access-Control-Allow-Origin and preflight 400; allowed origin is the configured one with credentials; methods and headers unchanged |
| Look unchanged | PASS by diff: no colour, gradient, blur or CSS changes in the PR (grep of added lines); new pages reuse existing components. Not compared pixel by pixel |
| Mock specs not weakened | PASS for accessibility.spec (56 added, 0 removed) and redesign.spec (4 added, 0 removed); sentry.spec changed, see V6-3 |

## Findings
V6-1 (Medium) SESSION_COOKIE_SECURE defaults to false (app/config.py:81). The production guard in app/main.py only checks scanning, and docker-compose.prod.yml does not set it, so a missing value in /etc/kien/kien.env means sign-in cookies without the Secure flag. Same class as D1; add it to the production guard.
V6-2 (Low) No CSRF token or Origin check. Protection is SameSite=Lax plus CORS preflight for JSON. Multipart upload endpoints are simple requests, so any page on a sibling *.kiensolutions.com host (same site) could submit them. Acceptable only while every such host is trusted.
V6-3 (Low) web/e2e/sentry.spec.ts now loads /sign-in instead of /, so the "no Sentry requests without a DSN" test no longer covers the signed-in portal.
V6-4 (Low) The default `build:cloudflare`, `deploy:demo` and CI use NEXT_PUBLIC_USE_MOCKS=true; only `build:cloudflare:production` is real. Nothing stops a real deployment using the demo build (it would show mock data, not leak real data). Document or guard.
V6-5 (Info, test backend only) During e2e:live the SQLite server logged one IntegrityError on audit_logs (firm_id, sequence) from concurrent requests. Production PostgreSQL serialises this with an advisory lock (app/audit.py:66). Not seen on PG.
