import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { audienceForHost } from "./audience.ts";

describe("audienceForHost", () => {
  it("serves firm subdomains as the client portal", () => {
    assert.equal(audienceForHost("northwind.kiensolutions.com"), "client");
    assert.equal(audienceForHost("Northwind.Kiensolutions.com:443"), "client");
  });
  it("serves the auditor host as the auditor portal", () => {
    assert.equal(audienceForHost("auditor.kiensolutions.com"), "auditor");
    assert.equal(audienceForHost("staff.example.test", "staff.example.test"), "auditor");
  });
  it("serves demo, dev and non-firm hosts as both", () => {
    for (const host of ["preview.kiensolutions.com", "design.kiensolutions.com", "kiensolutions.com", "www.kiensolutions.com", "localhost:3000", "kynetic.localhost:3100", "x.workers.dev", "", null, undefined, "elsewhere.test"])
      assert.equal(audienceForHost(host), "both", String(host));
  });
  it("does not treat nested labels as firms", () => {
    assert.equal(audienceForHost("a.b.kiensolutions.com"), "both");
  });
});
