/**
 * Which audience a hostname serves. One app, one Worker, two audiences:
 *  - clients  -> <firm>.kiensolutions.com (one host per firm, see tenant.ts)
 *  - auditors -> one fixed host (NEXT_PUBLIC_AUDITOR_HOST, default auditor.kiensolutions.com)
 *  - demo hosts (preview, localhost, workers.dev, apex) -> both, switchable in the sidebar
 *
 * The host only narrows what the UI offers. It is not authorization: the API must still
 * enforce role and firm on every call. TODO(auth): a session whose role does not
 * match the host's audience should be refused (see wrong-portal.tsx); the backend has no such check yet.
 */
/** Same value as PORTAL_APEX_HOST in tenant.ts (kept local so this file stays dependency-free for node tests). */
const PORTAL_APEX_HOST = "kiensolutions.com";

export type Audience = "client" | "auditor" | "both";

export const DEFAULT_AUDITOR_HOST = "auditor.kiensolutions.com";

/** Subdomains of the apex that are not firm portals. */
const NON_FIRM_LABELS = new Set(["www", "api", "app", "admin", "mail", "status", "preview", "design", "layout", "auditor"]);

function normalize(host: string | null | undefined): string {
  return (host ?? "").trim().toLowerCase().replace(/:\d+$/, "").replace(/\.$/, "");
}

export function audienceForHost(
  host: string | null | undefined,
  auditorHost: string = process.env.NEXT_PUBLIC_AUDITOR_HOST || DEFAULT_AUDITOR_HOST,
): Audience {
  const h = normalize(host);
  if (!h) return "both";
  if (h === normalize(auditorHost)) return "auditor";
  if (h === "localhost" || h.endsWith(".localhost") || h.endsWith(".workers.dev")) return "both";
  if (h === PORTAL_APEX_HOST) return "both";
  if (h.endsWith(`.${PORTAL_APEX_HOST}`)) {
    const label = h.slice(0, -(PORTAL_APEX_HOST.length + 1));
    if (label.includes(".") || NON_FIRM_LABELS.has(label)) return "both";
    return "client";
  }
  return "both";
}

/**
 * Firm branding is looked up from the host's firm label. The auditor host is not a firm, so the API
 * answers 404 there; asking would turn the auditor sign-in into the "Unknown firm" page.
 */
export function hostHasFirmBranding(
  host: string | null | undefined,
  auditorHost: string = process.env.NEXT_PUBLIC_AUDITOR_HOST || DEFAULT_AUDITOR_HOST,
): boolean {
  return audienceForHost(host, auditorHost) !== "auditor";
}

/** Browser helper; server and unknown contexts fall back to the demo behaviour. */
export function currentAudience(): Audience {
  return typeof window === "undefined" ? "both" : audienceForHost(window.location.host);
}

/** True when a signed-in role must not use a host that serves only the other audience. */
export function audienceRefusesRole(audience: Audience, role: "client" | "auditor"): boolean {
  return audience !== "both" && audience !== role;
}
