import assert from "node:assert/strict";
import { it } from "node:test";
import { checkBuildMode } from "./build-guard.mjs";

it("allows an explicit demo build and a plain real build", () => {
  assert.equal(checkBuildMode({ NEXT_PUBLIC_USE_MOCKS: "true", KIEN_BUILD_TARGET: "demo" }), null);
  assert.equal(checkBuildMode({}), null);
  assert.equal(checkBuildMode({ NEXT_PUBLIC_USE_MOCKS: "false", KIEN_BUILD_TARGET: "production" }), null);
  assert.equal(checkBuildMode({ KIEN_BUILD_TARGET: "production" }), null);
});
it("refuses a production build that uses the demo data", () => {
  assert.match(checkBuildMode({ NEXT_PUBLIC_USE_MOCKS: "true", KIEN_BUILD_TARGET: "production" }) ?? "", /real build must not use the demo/);
});
it("refuses a mock build that is not declared as the demo", () => {
  assert.match(checkBuildMode({ NEXT_PUBLIC_USE_MOCKS: "true" }) ?? "", /synthetic demo/);
  assert.match(checkBuildMode({ NEXT_PUBLIC_USE_MOCKS: "true", KIEN_BUILD_TARGET: "preview" }) ?? "", /synthetic demo/);
});
it("refuses an unknown target", () => {
  assert.match(checkBuildMode({ KIEN_BUILD_TARGET: "staging" }) ?? "", /Unknown KIEN_BUILD_TARGET/);
});
