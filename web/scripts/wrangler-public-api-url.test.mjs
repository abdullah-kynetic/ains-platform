import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { copyFileSync, mkdirSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";

const script = fileURLToPath(new URL("./wrangler-public-api-url.mjs", import.meta.url));

test("production API URL comes from wrangler env.production.vars", () => {
  const url = execFileSync(process.execPath, [script], { encoding: "utf8" });
  assert.equal(url, "https://api.kiensolutions.com");
});

function withConfig(source, check) {
  const root = mkdtempSync(path.join(tmpdir(), "kien-public-api-"));
  try {
    mkdirSync(path.join(root, "scripts"));
    const fixtureScript = path.join(root, "scripts", "public-api.mjs");
    copyFileSync(script, fixtureScript);
    writeFileSync(path.join(root, "wrangler.jsonc"), source);
    check(() => execFileSync(process.execPath, [fixtureScript], { encoding: "utf8", stdio: "pipe" }));
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
}

test("JSONC comments preserve the slashes inside an HTTPS URL", () => {
  withConfig(`{ // public build settings
    "env": { "production": { "vars": {
      "NEXT_PUBLIC_API_URL": "https://api.example.test"
    } } }
  }`, (run) => assert.equal(run(), "https://api.example.test"));
});

for (const url of [undefined, "http://localhost:8000", "https://api.example.test/"]) {
  test(`invalid production URL fails the build helper: ${String(url)}`, () => {
    withConfig(JSON.stringify({ env: { production: { vars: { NEXT_PUBLIC_API_URL: url } } } }),
      (run) => assert.throws(run, /must be an https URL with no trailing slash/));
  });
}
