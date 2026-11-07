import assert from "node:assert/strict";
import { it } from "node:test";
import { sanitizeSignInNext } from "./sign-in-next.ts";

it("preserves local paths, queries and fragments", () => {
  assert.equal(
    sanitizeSignInNext("/auditor?tab=tasks#latest"),
    "/auditor?tab=tasks#latest",
  );
});
it("rejects external, malformed and browser-normalized redirects", () => {
  for (const value of [
    null,
    undefined,
    "",
    "https://evil.invalid",
    "javascript:alert(1)",
    "//evil.invalid",
    "/\\evil.invalid",
    "/\n/evil.invalid",
    "/a/..//evil.invalid",
    " /auditor",
  ]) {
    assert.equal(sanitizeSignInNext(value), "/", String(value));
  }
});
