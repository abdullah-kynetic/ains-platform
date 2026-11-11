import assert from "node:assert/strict";
import test from "node:test";
import { apiConnectSources, contentSecurityPolicy, securityHeaders } from "./security-headers.mjs";

const prod = { NEXT_PUBLIC_API_URL: "https://api.kiensolutions.com" };

test("every required header is present", () => {
  const keys = securityHeaders(prod).map((h) => h.key);
  for (const key of [
    "Content-Security-Policy",
    "Strict-Transport-Security",
    "X-Frame-Options",
    "Referrer-Policy",
    "Permissions-Policy",
  ])
    assert.ok(keys.includes(key), key);
});

test("production CSP locks framing, plugins and unknown connections", () => {
  const csp = contentSecurityPolicy(prod);
  assert.match(csp, /frame-ancestors 'none'/);
  assert.match(csp, /object-src 'none'/);
  assert.match(csp, /base-uri 'self'/);
  assert.match(csp, /connect-src 'self' https:\/\/api\.kiensolutions\.com(;|$)/);
  assert.doesNotMatch(csp, /unsafe-eval/);
  assert.doesNotMatch(csp, /ws:/);
});

test("development CSP allows hot reload only in development", () => {
  assert.match(contentSecurityPolicy(prod, true), /unsafe-eval/);
});

test("the local {portal} API template becomes a localhost wildcard", () => {
  assert.deepEqual(apiConnectSources("http://{portal}:8000"), ["http://*.localhost:8000"]);
  assert.deepEqual(apiConnectSources(""), []);
});

test("a public Sentry DSN host is allowed, nothing else", () => {
  const csp = contentSecurityPolicy({ ...prod, NEXT_PUBLIC_SENTRY_DSN: "https://k@o1.ingest.sentry.io/2" });
  assert.match(csp, /https:\/\/o1\.ingest\.sentry\.io/);
});

test("an unset API URL falls back like the app does", () => {
  assert.match(contentSecurityPolicy({}, true), /http:\/\/localhost:8000/);
  assert.match(contentSecurityPolicy({}, false), /https:\/\/api\.kiensolutions\.com/);
});
