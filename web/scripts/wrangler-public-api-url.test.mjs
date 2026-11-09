import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { test } from "node:test";
import { fileURLToPath } from "node:url";

const script = fileURLToPath(new URL("./wrangler-public-api-url.mjs", import.meta.url));

test("production API URL comes from wrangler env.production.vars", () => {
  const url = execFileSync(process.execPath, [script], { encoding: "utf8" });
  assert.equal(url, "https://api.kiensolutions.com");
});
