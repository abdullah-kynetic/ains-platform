import { apiRequest, USE_MOCKS } from "../api";
import { delay, readStore, updateStore } from "../mock/store";
import { seedWorkpapers, CURRENT_USER, REVIEWER } from "../mock/seed";
import { logActivity } from "./log";
import type { Workpaper } from "./types";

const key = (id: string) => `kien-mock-workpapers-v1-${id}`;
const seed = (id: string) => () => (id === "eng-synthetic-001" ? seedWorkpapers() : []);

// TODO(backend): GET /auditor/engagements/{id}/workpapers -> Workpaper[] (one per checklist item that has one)
export async function listWorkpapers(engagementId: string): Promise<Workpaper[]> {
  if (!USE_MOCKS) return apiRequest(`/auditor/engagements/${encodeURIComponent(engagementId)}/workpapers`);
  return delay(readStore(key(engagementId), seed(engagementId)));
}

// TODO(backend): PUT /auditor/engagements/{id}/workpapers/{requestId} -> Workpaper
export async function saveWorkpaper(engagementId: string, input: Pick<Workpaper, "requestId" | "procedure" | "evidenceIds" | "conclusion">): Promise<Workpaper> {
  if (!USE_MOCKS) return apiRequest(`/auditor/engagements/${encodeURIComponent(engagementId)}/workpapers/${encodeURIComponent(input.requestId)}`, { method: "PUT", body: JSON.stringify(input) });
  let saved!: Workpaper;
  updateStore(key(engagementId), seed(engagementId), (rows) => {
    const existing = rows.find((r) => r.requestId === input.requestId);
    saved = { reviewer: "", reviewedAt: null, ...existing, ...input, preparer: CURRENT_USER, preparedAt: new Date().toISOString() };
    // Editing a reviewed workpaper clears the review so a second reviewer must look again.
    if (existing && (existing.procedure !== input.procedure || existing.conclusion !== input.conclusion)) { saved.reviewer = ""; saved.reviewedAt = null; }
    return [...rows.filter((r) => r.requestId !== input.requestId), saved];
  });
  logActivity(engagementId, `Saved workpaper for ${input.requestId}.`);
  return delay(saved);
}

// TODO(backend): POST /auditor/engagements/{id}/workpapers/{requestId}/review (reviewer must differ from preparer)
export async function reviewWorkpaper(engagementId: string, requestId: string): Promise<Workpaper[]> {
  if (!USE_MOCKS) {
    await apiRequest(`/auditor/engagements/${encodeURIComponent(engagementId)}/workpapers/${encodeURIComponent(requestId)}/review`, { method: "POST", body: "{}" });
    return listWorkpapers(engagementId);
  }
  const next = updateStore(key(engagementId), seed(engagementId), (rows) => {
    const row = rows.find((r) => r.requestId === requestId);
    if (row) { row.reviewer = REVIEWER; row.reviewedAt = new Date().toISOString(); }
  });
  logActivity(engagementId, `Reviewed workpaper for ${requestId}.`, REVIEWER);
  return delay(next);
}
