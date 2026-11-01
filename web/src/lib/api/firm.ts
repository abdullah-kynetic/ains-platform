import { delay, readStore, updateStore, writeStore, uid } from "../mock/store";
import { seedBranding, seedRubric, seedTeam, seedTemplates } from "../mock/seed";
import type { FirmBranding, RequestTemplate, RubricItem, TeamMember, TeamRole } from "./types";

const keys = { team: "kien-mock-team-v1", brand: "kien-mock-brand-v1", rubric: "kien-mock-rubric-v1", tpl: "kien-mock-templates-v1" };

// TODO(backend): GET /auditor/firm/team -> TeamMember[]
export const listTeam = () => delay(readStore(keys.team, seedTeam));
// TODO(backend): POST /auditor/firm/team {email, role} sends an invitation
export async function inviteMember(email: string, role: TeamRole): Promise<TeamMember[]> {
  const next = updateStore(keys.team, seedTeam, (t) => [...t, { id: uid("tm"), name: email.split("@")[0], email, role, status: "invited" as const }]);
  return delay(next);
}
// TODO(backend): PATCH /auditor/firm/team/{id} {role}
export async function changeRole(id: string, role: TeamRole): Promise<TeamMember[]> {
  return delay(updateStore(keys.team, seedTeam, (t) => { const m = t.find((x) => x.id === id); if (m) m.role = role; }));
}
// TODO(backend): DELETE /auditor/firm/team/{id}; the server blocks removing the last partner
export async function removeMember(id: string): Promise<TeamMember[]> {
  const team = readStore(keys.team, seedTeam);
  const target = team.find((m) => m.id === id);
  if (target?.role === "partner" && team.filter((m) => m.role === "partner").length === 1) throw new Error("A firm needs at least one partner.");
  return delay(updateStore(keys.team, seedTeam, (t) => t.filter((m) => m.id !== id)));
}

// TODO(backend): GET/PUT /auditor/firm/branding (logo goes to object storage, not a data URL)
export const getBranding = () => delay(readStore(keys.brand, seedBranding));
export const saveBranding = (b: FirmBranding) => delay(writeStore(keys.brand, b));

// TODO(backend): GET/PUT /auditor/firm/rubric; criteria stay empty until the partner approves them
export const getRubric = () => delay(readStore(keys.rubric, seedRubric));
export const saveRubricItem = (item: RubricItem) =>
  delay(updateStore(keys.rubric, seedRubric, (r) => { const i = r.findIndex((x) => x.requestId === item.requestId); if (i >= 0) r[i] = item; }));

// TODO(backend): CRUD /auditor/firm/request-templates
export const listTemplates = () => delay(readStore(keys.tpl, seedTemplates));
export async function saveTemplate(t: Omit<RequestTemplate, "id"> & { id?: string }): Promise<RequestTemplate[]> {
  const full: RequestTemplate = { ...t, id: t.id ?? uid("tpl") };
  return delay(updateStore(keys.tpl, seedTemplates, (all) => [...all.filter((x) => x.id !== full.id), full]));
}
export const deleteTemplate = (id: string) => delay(updateStore(keys.tpl, seedTemplates, (all) => all.filter((x) => x.id !== id || x.id === "tpl-all")));
