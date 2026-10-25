import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  KIEN_DEFAULT_BRANDING,
  brandingForKnownSlug,
  firmSlugFromHost,
  interpretBrandingResponse,
  mockBrandingForSlug,
  safeLogoUrl,
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

describe("branding", () => {
  it("keeps the synthetic mock and Kien defaults", () => {
    assert.deepEqual(mockBrandingForSlug("kynetic"), {
      name: "Kynetic",
      logoUrl: "/brand/kynetic-mark.svg",
    });
    assert.deepEqual(mockBrandingForSlug("northwind"), KIEN_DEFAULT_BRANDING);
    assert.deepEqual(
      brandingForKnownSlug("kynetic"),
      process.env.NEXT_PUBLIC_USE_MOCKS === "true"
        ? mockBrandingForSlug("kynetic")
        : KIEN_DEFAULT_BRANDING,
    );
  });

  it("accepts a 200 name with an https or site-path logo", () => {
    assert.deepEqual(
      interpretBrandingResponse(200, {
        name: "Synthetic Alpha Securities",
        logoUrl: "/brand/synthetic-alpha.svg",
      }),
      {
        status: "ok",
        branding: {
          name: "Synthetic Alpha Securities",
          logoUrl: "/brand/synthetic-alpha.svg",
        },
      },
    );
    assert.equal(
      safeLogoUrl("https://cdn.example/logo.svg"),
      "https://cdn.example/logo.svg",
    );
  });

  it("falls back when logoUrl is null or unsafe", () => {
    assert.deepEqual(
      interpretBrandingResponse(200, { name: "Plain Synthetic", logoUrl: null }),
      { status: "ok", branding: { name: "Plain Synthetic", logoUrl: null } },
    );
    assert.equal(safeLogoUrl("http://cdn.example/logo.svg"), null);
    assert.equal(safeLogoUrl("javascript:alert(1)"), null);
  });

  it("treats the unknown-firm 404 as unknown and keeps defaults otherwise", () => {
    assert.deepEqual(
      interpretBrandingResponse(404, { detail: "Unknown firm portal" }),
      { status: "unknown" },
    );
    assert.deepEqual(interpretBrandingResponse(404, { detail: "Missing" }), {
      status: "unavailable",
    });
    assert.deepEqual(interpretBrandingResponse(500, null), {
      status: "unavailable",
    });
  });
});
