import { USE_MOCKS } from "../api";
import { contractRequest } from "./contract";
import { delay, readStore, updateStore, writeStore, uid } from "../mock/store";
import { seedBranding, seedRubric, seedTeam, seedTemplates } from "../mock/seed";
import type { FirmBranding, RequestTemplate, RubricItem, TeamMember, TeamRole } from "./types";

const keys = { team: "kien-mock-team-v1", brand: "kien-mock-brand-v1", rubric: "kien-mock-rubric-v1", tpl: "kien-mock-templates-v1" };

// Contract: GET /auditor/firm/team -> TeamMember[]
export const listTeam = (): Promise<TeamMember[]> => USE_MOCKS
  ? delay(readStore(keys.team, seedTeam)) : contractRequest("/auditor/firm/team");
// Contract: POST /auditor/firm/team {email, role} sends an invitation
export async function inviteMember(email: string, role: TeamRole): Promise<TeamMember[]> {
  if (!USE_MOCKS) return contractRequest("/auditor/firm/team", { method: "POST", body: JSON.stringify({ email, role }) });
  const next = updateStore(keys.team, seedTeam, (t) => [...t, { id: uid("tm"), name: email.split("@")[0], email, role, status: "invited" as const }]);
  return delay(next);
}
// Contract: PATCH /auditor/firm/team/{id} {role}
export async function changeRole(id: string, role: TeamRole): Promise<TeamMember[]> {
  if (!USE_MOCKS) return contractRequest(`/auditor/firm/team/${encodeURIComponent(id)}`, { method: "PATCH", body: JSON.stringify({ role }) });
  return delay(updateStore(keys.team, seedTeam, (t) => { const m = t.find((x) => x.id === id); if (m) m.role = role; }));
}
// Contract: DELETE /auditor/firm/team/{id}; the server blocks removing the last partner
export async function removeMember(id: string): Promise<TeamMember[]> {
  if (!USE_MOCKS) return contractRequest(`/auditor/firm/team/${encodeURIComponent(id)}`, { method: "DELETE" });
  const team = readStore(keys.team, seedTeam);
  const target = team.find((m) => m.id === id);
  if (target?.role === "partner" && team.filter((m) => m.role === "partner").length === 1) throw new Error("A firm needs at least one partner.");
  return delay(updateStore(keys.team, seedTeam, (t) => t.filter((m) => m.id !== id)));
}

// Contract: GET/PUT /auditor/firm/branding (logo goes to object storage, not a data URL)
export const getBranding = (): Promise<FirmBranding> => USE_MOCKS
  ? delay(readStore(keys.brand, seedBranding)) : contractRequest("/auditor/firm/branding");
export const saveBranding = (b: FirmBranding): Promise<FirmBranding> => USE_MOCKS
  ? delay(writeStore(keys.brand, b)) : contractRequest("/auditor/firm/branding", { method: "PUT", body: JSON.stringify(b) });

// Contract: GET/PUT /auditor/firm/rubric; criteria stay empty until the partner approves them
export const getRubric = (): Promise<RubricItem[]> => USE_MOCKS
  ? delay(readStore(keys.rubric, seedRubric)) : contractRequest("/auditor/firm/rubric");
export const saveRubricItem = (item: RubricItem): Promise<RubricItem[]> => !USE_MOCKS
  ? contractRequest("/auditor/firm/rubric", { method: "PUT", body: JSON.stringify(item) })
  : delay(updateStore(keys.rubric, seedRubric, (r) => { const i = r.findIndex((x) => x.requestId === item.requestId); if (i >= 0) r[i] = item; }));

// Contract: CRUD /auditor/firm/request-templates
export const listTemplates = (): Promise<RequestTemplate[]> => USE_MOCKS
  ? delay(readStore(keys.tpl, seedTemplates)) : contractRequest("/auditor/firm/request-templates");
export async function saveTemplate(t: Omit<RequestTemplate, "id"> & { id?: string }): Promise<RequestTemplate[]> {
  if (!USE_MOCKS) return contractRequest(`/auditor/firm/request-templates${t.id ? `/${encodeURIComponent(t.id)}` : ""}`, { method: t.id ? "PUT" : "POST", body: JSON.stringify(t) });
  const full: RequestTemplate = { ...t, id: t.id ?? uid("tpl") };
  return delay(updateStore(keys.tpl, seedTemplates, (all) => [...all.filter((x) => x.id !== full.id), full]));
}
export const deleteTemplate = (id: string): Promise<RequestTemplate[]> => !USE_MOCKS
  ? contractRequest(`/auditor/firm/request-templates/${encodeURIComponent(id)}`, { method: "DELETE" })
  : delay(updateStore(keys.tpl, seedTemplates, (all) => all.filter((x) => x.id !== id || x.id === "tpl-all")));

/** File bytes go to the API; only its object-storage URL is saved in branding. */
export async function uploadBrandingLogo(file: File): Promise<{ logoUrl: string }> {
  if (!/^image\/(png|jpeg|svg\+xml)$/.test(file.type)) throw new Error("Use a PNG, JPG or SVG logo.");
  if (!file.size || file.size > 512 * 1024) throw new Error("Logo must be nonempty and under 512 KB.");
  if (USE_MOCKS) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve({ logoUrl: String(reader.result) });
      reader.onerror = () => reject(new Error("Could not read the logo."));
      reader.readAsDataURL(file);
    });
  }
  const body = new FormData();
  body.append("file", file);
  const result = await contractRequest<{ logoUrl: string }>("/auditor/firm/branding/logo", { method: "POST", body });
  let valid = false;
  if (typeof result.logoUrl === "string" && !result.logoUrl.includes("\\")) {
    if (/^\/(?!\/)/.test(result.logoUrl)) valid = true;
    else {
      try {
        const url = new URL(result.logoUrl);
        valid = url.protocol === "https:" && !url.username && !url.password;
      } catch { /* Invalid server URL stays unavailable. */ }
    }
  }
  if (!valid) {
    throw new Error("The server did not return a valid logo URL.");
  }
  return result;
}
