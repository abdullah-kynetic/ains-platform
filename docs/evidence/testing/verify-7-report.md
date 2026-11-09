# VERIFY-7 report: PR #87 at 4ebfe3e9e319de4a5937ec6f48e02f704846aa30

Environment: sandbox, Python 3.12.3, Node (npm ci), PostgreSQL 16.15 as `postgres`, Playwright Chromium. Synthetic data only. No code fixed.

## Checks
| Check | Result |
|---|---|
| ruff, eslint, tsc | PASS |
| `npm run test:unit` | PASS: 22 |
| Backend suite excl. PG files | PASS: 348 passed |
| PG files as non-root, PostgreSQL 16.15 | PASS: 11 passed |
| `npm run test:e2e:live` (real backend) | PASS: 8 of 8 |
| Full mock `npm run test:e2e` | 81 passed, 1 failed: tasks.spec.ts:22 (known, PR #86). b3b02ac is reverted (bc47167) |
| Demo build `KIEN_BUILD_TARGET=demo NEXT_PUBLIC_USE_MOCKS=true next build` | PASS |
| Production build `KIEN_BUILD_TARGET=production NEXT_PUBLIC_USE_MOCKS=false next build` | PASS |

## V6-1 to V6-4
- V6-1 FIXED: production start refuses without SESSION_COOKIE_SECURE=true; compose sets it. Removing the guard, or setting compose to "false", each fails a test.
- V6-2 FIXED (see probe): new OriginCheckMiddleware on POST/PUT/PATCH/DELETE, exact match against CORS_ORIGINS.
- V6-3 FIXED: sentry spec now covers both the signed-in portal and the sign-in page; both pass.
- V6-4 FIXED: build guard runs at `next build` (PHASE_PRODUCTION_BUILD). Real builds: mocks without a declared target refused; production with mocks refused; unknown target refused; declared demo and plain real builds allowed. Mutating either rule fails a unit test.

## Origin check probe (own, against the real app)
403: evil Origin, Origin "null", sibling subdomain, suffix trick (allowed.evil.com), userinfo trick (allowed@evil.com), evil Referer only, unparsable Referer, empty Origin, evil Origin with an allowed Referer. Cookie-authenticated POST sign-out, multipart upload and PATCH from an evil Origin: 403, and the session stayed valid. 200: allowed Origin (any host case), allowed Referer only, and GET with an evil Origin (CORS handles reads; unchanged).
No Origin and no Referer passes (200). Judgement: safe for cookie auth in current browsers. Browsers send Origin on every cross-origin POST (including multipart form posts) and sandboxed or redirected cases send "null", which is refused. SameSite=Lax independently withholds the cookie on cross-site POST. Remaining exposure is only a non-browser client, which has no ambient cookie.

## Findings
V7-1 (Low, test gap) Mutations that accept Origin "null"/unparsable values, and that restrict checking to POST only (PATCH/PUT/DELETE unchecked), both pass tests/test_origin_check.py. The real code is correct (probe). Add tests for "null" and for PATCH.
V7-2 (Low, operational) The allowlist is the exact CORS_ORIGINS list. If portal hosts are per firm, every firm origin must be listed or legitimate POSTs get 403 "Cross-site request refused". Confirm this is intended before real firms are onboarded.
V7-3 (Low) A production build still contains the demo mock code and strings (for example "Demo Auditor" appears in a production chunk) as unreachable branches, gated at runtime by USE_MOCKS=false. Not exploitable, but the build guard cannot stop a mislabelled deployment; `KIEN_BUILD_TARGET=demo` with mocks off passes.
V7-4 (Info, SQLite test backend only) e2e:live logs more audit_logs sequence IntegrityErrors than before (concurrent requests on SQLite). PostgreSQL serialises with an advisory lock (app/audit.py:66). Not reproduced on PostgreSQL.
