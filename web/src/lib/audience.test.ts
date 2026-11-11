import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { audienceForHost, audienceRefusesRole, hostHasFirmBranding } from "./audience.ts";

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

describe("audienceRefusesRole", () => {
  it("refuses a role on the other audience's host", () => {
    assert.equal(audienceRefusesRole("client", "auditor"), true);
    assert.equal(audienceRefusesRole("auditor", "client"), true);
  });
  it("allows the matching role and any role on demo hosts", () => {
    assert.equal(audienceRefusesRole("client", "client"), false);
    assert.equal(audienceRefusesRole("auditor", "auditor"), false);
    assert.equal(audienceRefusesRole("both", "client"), false);
    assert.equal(audienceRefusesRole("both", "auditor"), false);
  });
});

describe("hostHasFirmBranding", () => {
  it("skips the firm branding lookup on the auditor host only", () => {
    assert.equal(hostHasFirmBranding("auditor.kiensolutions.com"), false);
    assert.equal(hostHasFirmBranding("Auditor.KienSolutions.com:443"), false);
    assert.equal(hostHasFirmBranding("demo-securities.kiensolutions.com"), true);
    assert.equal(hostHasFirmBranding("kynetic.localhost:3000"), true);
    assert.equal(hostHasFirmBranding("auditor.example.test", "auditor.example.test"), false);
  });
});
