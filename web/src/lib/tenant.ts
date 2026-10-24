/**
 * Firm host for the single portal deploy.
 * kiensolutions.com and www stay on the landing Worker.
 */

export const PORTAL_APEX_HOST = "kiensolutions.com";

export type TenantBranding = {
  name: string;
  logoUrl: string;
};

/** Shown until a firm has its own name and logo. */
export const KIEN_DEFAULT_BRANDING: TenantBranding = {
  name: "Kien",
  logoUrl: "/brand/kien-mark.svg",
};

export type TenantResolution =
  | { ok: true; slug: string }
  | { ok: false; reason: "apex" | "www" | "missing" };

const FIRM_LABEL = /^(?:[a-z0-9]|[a-z0-9][a-z0-9-]{0,61}[a-z0-9])$/;

/**
 * Synthetic stand-ins. The API will later supply per-firm name and logoUrl.
 * This module does not call the network.
 */
const MOCK_FIRM_BRANDING: Record<string, TenantBranding> = {
  kynetic: {
    name: "Kynetic",
    logoUrl: "/brand/kynetic-mark.svg",
  },
};

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
  if (!host || host.length > 253 || !/^[a-z0-9.-]+$/.test(host)) return "";
  return host;
}

export async function getTenantBranding(slug: string): Promise<TenantBranding> {
  const branded = MOCK_FIRM_BRANDING[slug];
  if (!branded) return KIEN_DEFAULT_BRANDING;
  return {
    name: branded.name.trim() || KIEN_DEFAULT_BRANDING.name,
    logoUrl: branded.logoUrl.trim() || KIEN_DEFAULT_BRANDING.logoUrl,
  };
}
