import assert from "node:assert/strict";
import { it } from "node:test";
import { lockoutText, signInErrorText } from "./sign-in-message.ts";

it("explains a lockout with the wait time", () => {
  assert.match(lockoutText(30), /about a minute/);
  assert.match(lockoutText(600), /about 10 minutes/);
  assert.equal(lockoutText(null), "Too many failed attempts. Try again later.");
  assert.equal(signInErrorText({ status: 429, message: "x", retryAfterSeconds: 900 }, "credentials"), lockoutText(900));
});
it("never says which credential was wrong", () => {
  const text = signInErrorText({ status: 401, message: "Invalid email or password" }, "credentials");
  assert.equal(text, "Email or password is incorrect");
});
it("uses a code-specific message on the MFA step and a neutral one for other errors", () => {
  assert.match(signInErrorText({ status: 401, message: "Invalid MFA code" }, "mfa"), /code is not valid/);
  assert.match(signInErrorText({ status: 503, message: "x" }, "credentials"), /temporarily unavailable/);
  assert.match(signInErrorText({ status: 500, message: "x" }, "credentials"), /could not be completed/);
});
