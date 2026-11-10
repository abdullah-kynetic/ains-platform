import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { after, afterEach, test } from "node:test";
import ts from "typescript";

// Node's strip-types loader cannot resolve the app's extensionless imports.
// Transpile the actual API graph with the project's compiler, without a bundle.
const require = createRequire(import.meta.url);
const previousLoader = require.extensions[".ts"];
require.extensions[".ts"] = (module, filename) => {
  const result = ts.transpileModule(readFileSync(filename, "utf8"), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, esModuleInterop: true },
  });
  module._compile(result.outputText, filename);
};
const { contractRequest, NotAvailableError } = require("../src/lib/api/contract.ts");
const { ApiError } = require("../src/lib/api.ts");
const firm = require("../src/lib/api/firm.ts");
const fetchBefore = globalThis.fetch;
afterEach(() => { globalThis.fetch = fetchBefore; });
after(() => { require.extensions[".ts"] = previousLoader; });

function respond(status, detail) {
  globalThis.fetch = async () => new Response(JSON.stringify({ detail }), { status });
}

test("unmerged contract gives a typed unavailable state", async () => {
  respond(404, "Not Found");
  await assert.rejects(contractRequest("/auditor/firm/team"), NotAvailableError);
});
for (const [status, detail] of [[401, "Not authenticated"], [403, "Forbidden"], [404, "Member not found"], [422, "Invalid role"]]) {
  test(`contract preserves ${status} server rejection and never substitutes seed data`, async () => {
    respond(status, detail);
    await assert.rejects(firm.listTeam(), (error) => error instanceof ApiError && error.status === status && error.message === detail);
  });
}

test("team mutations use credentialed JSON and escape opaque member IDs", async () => {
  const calls = [];
  globalThis.fetch = async (url, init) => {
    calls.push({ path: new URL(url).pathname, ...init });
    return Response.json([]);
  };
  await firm.inviteMember("synthetic@example.test", "reviewer");
  await firm.changeRole("member/other", "auditor");
  await firm.removeMember("member/other");
  assert.deepEqual(calls.map(({ path, method }) => [path, method]), [
    ["/auditor/firm/team", "POST"],
    ["/auditor/firm/team/member%2Fother", "PATCH"],
    ["/auditor/firm/team/member%2Fother", "DELETE"],
  ]);
  assert.ok(calls.every((call) => call.credentials === "include"));
  assert.equal(calls[0].headers["Content-Type"], "application/json");
  assert.deepEqual(JSON.parse(calls[0].body), { email: "synthetic@example.test", role: "reviewer" });
});

test("logo uploads file bytes as multipart, without a JSON Content-Type", async () => {
  const file = new File(["synthetic-image-bytes"], "synthetic.png", { type: "image/png" });
  globalThis.fetch = async (url, init) => {
    assert.equal(new URL(url).pathname, "/auditor/firm/branding/logo");
    assert.equal(init.method, "POST");
    assert.equal(init.credentials, "include");
    assert.equal(init.headers["Content-Type"], undefined);
    assert.ok(init.body instanceof FormData);
    assert.equal(await init.body.get("file").text(), "synthetic-image-bytes");
    return Response.json({ logoUrl: "https://storage.example.test/synthetic.png" });
  };
  assert.deepEqual(await firm.uploadBrandingLogo(file), { logoUrl: "https://storage.example.test/synthetic.png" });
});

test("live logo upload rejects a data URL response", async () => {
  globalThis.fetch = async () => Response.json({ logoUrl: "data:image/png;base64,c3ludGhldGlj" });
  await assert.rejects(firm.uploadBrandingLogo(new File(["synthetic"], "synthetic.png", { type: "image/png" })), /valid logo URL/);
});

test("branding, rubric and templates save through their contracts", async () => {
  const calls = [];
  globalThis.fetch = async (url, init) => {
    calls.push({ path: new URL(url).pathname, ...init });
    return Response.json([]);
  };
  const branding = { name: "Synthetic Firm", logoUrl: null, tagline: "Synthetic" };
  await firm.saveBranding(branding);
  await firm.saveRubricItem({ requestId: "AML-BD-001", criteria: "", enabled: true });
  await firm.saveTemplate({ name: "Synthetic", kind: "custom", description: "", requestIds: ["AML-BD-001"] });
  await firm.deleteTemplate("template/other");
  assert.deepEqual(calls.map(({ path, method }) => [path, method]), [
    ["/auditor/firm/branding", "PUT"], ["/auditor/firm/rubric", "PUT"],
    ["/auditor/firm/request-templates", "POST"], ["/auditor/firm/request-templates/template%2Fother", "DELETE"],
  ]);
  assert.deepEqual(JSON.parse(calls[0].body), branding);
});
