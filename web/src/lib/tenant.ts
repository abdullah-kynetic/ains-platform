/**
 * Firm host for the single portal deploy.
 * kiensolutions.com and www stay on the landing Worker.
 */

export const PORTAL_APEX_HOST = "kiensolutions.com";

export const KIEN_MARK_SRC = "/brand/kien-mark.svg";

/** Display branding. `logoUrl` is null until a firm logo replaces the Kien mark. */
export type TenantBranding = {
  name: string;
  logoUrl: string | null;
};

/** Shown while branding loads, and when the branding request fails. */
export const KIEN_DEFAULT_BRANDING: TenantBranding = {
  name: "Kien",
  logoUrl: null,
};

export type TenantRejection = "apex" | "www" | "missing" | "unlisted";

export type TenantResolution =
  | { ok: true; slug: string }
  | { ok: false; reason: TenantRejection };

export type BrandingLoad =
  | { status: "ok"; branding: TenantBranding }
  | { status: "unknown" }
  | { status: "unavailable" };

export const UNKNOWN_FIRM_DETAIL = "Unknown firm portal";

const FIRM_LABEL = /^(?:[a-z0-9]|[a-z0-9][a-z0-9-]{0,61}[a-z0-9])$/;

/** Synthetic stand-in used when `NEXT_PUBLIC_USE_MOCKS=true`. */
const MOCK_FIRM_BRANDING: Record<string, TenantBranding> = {
  kynetic: {
    name: "Kynetic",
    logoUrl: "/brand/kynetic-mark.svg",
  },
};

export function mockBrandingForSlug(slug: string): TenantBranding {
  return MOCK_FIRM_BRANDING[slug] ?? KIEN_DEFAULT_BRANDING;
}

/** First paint. Live portals stay on the Kien defaults until the API responds. */
export function brandingForKnownSlug(slug: string): TenantBranding {
  if (process.env.NEXT_PUBLIC_USE_MOCKS === "true") return mockBrandingForSlug(slug);
  return KIEN_DEFAULT_BRANDING;
}

export function safeLogoUrl(value: string | null | undefined): string | null {
  if (!value) return null;
  const logo = value.trim();
  if (!logo || logo !== value || logo.includes("\\") || logo.includes("..")) return null;
  if (logo.startsWith("/") && !logo.startsWith("//")) return logo;
  try {
    const url = new URL(logo);
    if (url.protocol === "https:") return url.toString();
  } catch {
    return null;
  }
  return null;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

/** Map a `/tenant/branding` response. Does not call the network. */
export function interpretBrandingResponse(
  status: number,
  body: unknown,
): BrandingLoad {
  if (
    status === 404 &&
    isRecord(body) &&
    body.detail === UNKNOWN_FIRM_DETAIL
  ) {
    return { status: "unknown" };
  }
  if (status !== 200 || !isRecord(body) || typeof body.name !== "string") {
    return { status: "unavailable" };
  }
  if (body.logoUrl != null && typeof body.logoUrl !== "string") {
    return { status: "unavailable" };
  }
  const name = body.name.trim();
  if (!name) return { status: "unavailable" };
  return {
    status: "ok",
    branding: {
      name,
      logoUrl: safeLogoUrl(typeof body.logoUrl === "string" ? body.logoUrl : null),
    },
  };
}

export function hostnameFromHeader(
  hostHeader: string | null | undefined,
): string {
  if (!hostHeader) return "";
  let value = hostHeader.trim().toLowerCase();
  if (!value) return "";
  if (value.startsWith("[")) {
    const end = value.indexOf("]");
    return end === -1 ? "" : value.slice(0, end + 1);
  }
  const colon = value.lastIndexOf(":");
  if (colon > -1) value = value.slice(0, colon);
  if (value.endsWith(".")) value = value.slice(0, -1);
  return value;
}

function labelBefore(host: string, parent: string): string | null {
  const suffix = `.${parent}`;
  if (!host.endsWith(suffix)) return null;
  const label = host.slice(0, -suffix.length);
  if (!label || label.includes(".")) return null;
  return label;
}

/**
 * Read the firm slug from the request host.
 * Production: `<slug>.kiensolutions.com`. Development: `<slug>.localhost`.
 */
export function firmSlugFromHost(
  hostHeader: string | null | undefined,
): TenantResolution {
  const host = hostnameFromHeader(hostHeader);
  if (!host) return { ok: false, reason: "missing" };
  if (host === PORTAL_APEX_HOST) return { ok: false, reason: "apex" };
  if (host === `www.${PORTAL_APEX_HOST}` || host === "www.localhost") {
    return { ok: false, reason: "www" };
  }

  const slug =
    labelBefore(host, PORTAL_APEX_HOST) ?? labelBefore(host, "localhost");
  if (!slug || slug === "www" || !FIRM_LABEL.test(slug)) {
    return { ok: false, reason: slug === "www" ? "www" : "missing" };
  }
  return { ok: true, slug };
}

export function safeHostLabel(hostHeader: string | null | undefined): string {
  const host = hostnameFromHeader(hostHeader);
  if (!host || host.length > 253 || !/^[a-z0-9.:-]+$/.test(host)) return "";
  return host;
}
