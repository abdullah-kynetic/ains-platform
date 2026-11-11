import { apiRequest, USE_MOCKS } from "../api";
import { delay, readStore, updateStore, uid } from "../mock/store";
import { seedFindings } from "../mock/seed";
import { logActivity } from "./log";
import type { Finding, FindingStatus } from "./types";

const key = "kien-mock-findings-v1";
const all = () => readStore<Finding[]>(key, seedFindings);

export type FindingInput = Omit<Finding, "id" | "status" | "managementResponse" | "respondedAt" | "updatedAt">;

/** A finding cannot be approved or issued without every field and at least one document + page citation. */
export function findingBlockers(f: Pick<Finding, "title" | "rule" | "condition" | "cause" | "effect" | "recommendation" | "citations">): string[] {
  const missing = (["title", "rule", "condition", "cause", "effect", "recommendation"] as const).filter((k) => !f[k].trim());
  return [...missing.map((k) => `Add the ${k}.`), ...(f.citations.length ? [] : ["Cite at least one document and page."])];
}

// GET /auditor/engagements/{id}/findings -> Finding[] (docs/kb/26-findings-api.md)
export async function listFindings(engagementId: string): Promise<Finding[]> {
  if (!USE_MOCKS) return apiRequest(`/auditor/engagements/${encodeURIComponent(engagementId)}/findings`);
  return delay(all().filter((f) => f.engagementId === engagementId));
}

// POST/PUT /auditor/engagements/{id}/findings[/{findingId}]; editing an approved finding returns it to draft
export async function saveFinding(engagementId: string, input: FindingInput, id?: string): Promise<Finding> {
  if (!USE_MOCKS) {
    const { title, rule, condition, cause, effect, recommendation, severity, citations } = input;
    const base = `/auditor/engagements/${encodeURIComponent(engagementId)}/findings`;
    return apiRequest(id ? `${base}/${encodeURIComponent(id)}` : base, { method: id ? "PUT" : "POST", body: JSON.stringify({ title, rule, condition, cause, effect, recommendation, severity, citations }) });
  }
  let saved!: Finding;
  updateStore(key, seedFindings, (rows) => {
    const existing = rows.find((r) => r.id === id);
    saved = { ...input, engagementId, id: existing?.id ?? uid("fnd"), status: "draft", managementResponse: existing?.managementResponse ?? "", respondedAt: existing?.respondedAt ?? null, updatedAt: new Date().toISOString() };
    return [...rows.filter((r) => r.id !== saved.id), saved];
  });
  logActivity(engagementId, `${id ? "Edited" : "Drafted"} finding “${input.title}”.`);
  return delay(saved);
}

const allowed: Record<FindingStatus, FindingStatus[]> = { draft: ["approved"], approved: ["draft"], issued: ["closed"], responded: ["closed"], closed: [] };

// POST /auditor/findings/{id}/status {status}. Server enforces transitions, citations and that only an auditor acts.
export async function setFindingStatus(id: string, status: FindingStatus): Promise<Finding> {
  if (!USE_MOCKS) return apiRequest(`/auditor/findings/${encodeURIComponent(id)}/status`, { method: "POST", body: JSON.stringify({ status }) });
  let result: Finding | undefined;
  updateStore(key, seedFindings, (rows) => {
    const f = rows.find((r) => r.id === id);
    if (!f) return;
    if (!allowed[f.status].includes(status)) throw new Error(`A ${f.status} finding cannot move to ${status}.`);
    if (status === "approved" || status === "issued") { const b = findingBlockers(f); if (b.length) throw new Error(b[0]); }
    f.status = status; f.updatedAt = new Date().toISOString(); result = f;
  });
  if (!result) throw new Error("Finding not found.");
  logActivity(result.engagementId, `Marked finding “${result.title}” as ${status}.`);
  return delay(result);
}

// DELETE /auditor/findings/{id} (drafts only)
export async function deleteDraftFinding(id: string): Promise<void> {
  if (!USE_MOCKS) return apiRequest(`/auditor/findings/${encodeURIComponent(id)}`, { method: "DELETE" });
  updateStore(key, seedFindings, (rows) => rows.filter((r) => !(r.id === id && r.status === "draft")));
  return delay(undefined, 0);
}
