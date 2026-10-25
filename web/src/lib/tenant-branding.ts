import { API_URL } from "@/lib/api";
import { interpretBrandingResponse, type BrandingLoad } from "@/lib/tenant";

/** Public branding. The API reads the firm from this browser's Origin. */
export async function fetchTenantBranding(): Promise<BrandingLoad> {
  try {
    const response = await fetch(`${API_URL}/tenant/branding`, {
      credentials: "include",
      cache: "no-store",
    });
    const body = (await response.json().catch(() => null)) as unknown;
    return interpretBrandingResponse(response.status, body);
  } catch {
    return { status: "unavailable" };
  }
}
