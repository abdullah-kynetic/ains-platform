import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  KIEN_DEFAULT_BRANDING,
  firmSlugFromHost,
  getTenantBranding,
} from "./tenant.ts";

describe("firmSlugFromHost", () => {
  it("reads a production firm subdomain", () => {
    assert.deepEqual(firmSlugFromHost("kynetic.kiensolutions.com"), {
      ok: true,
      slug: "kynetic",
    });
    assert.deepEqual(firmSlugFromHost("Kynetic.Kiensolutions.com:443"), {
      ok: true,
      slug: "kynetic",
    });
    assert.deepEqual(firmSlugFromHost("north-wind.kiensolutions.com."), {
      ok: true,
      slug: "north-wind",
    });
  });

  it("reads a dev firm subdomain and ignores the port", () => {
    assert.deepEqual(firmSlugFromHost("kynetic.localhost"), {
      ok: true,
      slug: "kynetic",
    });
    assert.deepEqual(firmSlugFromHost("kynetic.localhost:3000"), {
      ok: true,
      slug: "kynetic",
    });
  });

  it("rejects the apex, www, and a missing slug", () => {
    assert.deepEqual(firmSlugFromHost("kiensolutions.com"), {
      ok: false,
      reason: "apex",
    });
    assert.deepEqual(firmSlugFromHost("kiensolutions.com:443"), {
      ok: false,
      reason: "apex",
    });
    assert.deepEqual(firmSlugFromHost("www.kiensolutions.com"), {
      ok: false,
      reason: "www",
    });
    assert.deepEqual(firmSlugFromHost("www.localhost:3000"), {
      ok: false,
      reason: "www",
    });
    for (const host of [
      null,
      undefined,
      "",
      "localhost",
      "localhost:3000",
      "127.0.0.1:3100",
      "[::1]:3000",
      "a.b.kiensolutions.com",
      "kynetic.example.com",
      "ains-platform-demo.ains-web.workers.dev",
      "-bad.localhost",
      "bad-.kiensolutions.com",
    ]) {
      assert.equal(firmSlugFromHost(host).ok, false, String(host));
    }
  });
});

describe("getTenantBranding", () => {
  it("returns mock firm branding and Kien defaults", async () => {
    assert.deepEqual(await getTenantBranding("kynetic"), {
      name: "Kynetic",
      logoUrl: "/brand/kynetic-mark.svg",
    });
    assert.deepEqual(await getTenantBranding("northwind"), KIEN_DEFAULT_BRANDING);
  });
});
