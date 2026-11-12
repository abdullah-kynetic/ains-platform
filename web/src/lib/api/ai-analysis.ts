import { ApiError, apiRequest, USE_MOCKS } from "../api";

export type AiDraftKind = "finding" | "document_flag" | "client_request";
export type AiDraftStatus = "pending" | "accepted" | "rejected";

/** Auditor-only. Clients never receive any of these fields from any route. */
export type AiDraft = {
  id: string;
  runId: string;
  kind: AiDraftKind;
  itemKey: string;
  documentId: string;
  documentName: string;
  page: number;
  title: string;
  body: string;
  model: string;
  status: AiDraftStatus;
  edited: boolean;
  findingId: string | null;
  createdAt: string;
};

export type AiSkipped = { documentId: string; document: string; code: string; reason: string };
export type AiRun = { id: string; createdAt: string; documentsAnalyzed: number; models: string[]; skipped: AiSkipped[] };
export type AiAnalysis = { drafts: AiDraft[]; lastRun: AiRun | null };

const base = (engagementId: string) => `/auditor/engagements/${encodeURIComponent(engagementId)}/ai-analysis`;

/**
 * GET /auditor/engagements/{id}/ai-analysis. Returns null when the feature is switched off (the
 * server answers 404 for every AI route then) so the panel and its button stay hidden.
 */
export async function getAiAnalysis(engagementId: string): Promise<AiAnalysis | null> {
  if (USE_MOCKS) return null; // no synthetic backend for AI drafts; the demo build hides the panel
  try {
    return await apiRequest<AiAnalysis>(base(engagementId));
  } catch (error) {
    if (error instanceof ApiError && (error.status === 404 || error.status === 403)) return null;
    throw error;
  }
}

/** POST /auditor/engagements/{id}/ai-analysis/run. Drafts only; nothing reaches a client. */
export function runAiAnalysis(engagementId: string): Promise<AiAnalysis> {
  return apiRequest(`${base(engagementId)}/run`, { method: "POST" });
}

export function acceptAiDraft(id: string): Promise<AiDraft> {
  return apiRequest(`/auditor/ai-drafts/${encodeURIComponent(id)}/accept`, { method: "POST" });
}

export function rejectAiDraft(id: string): Promise<AiDraft> {
  return apiRequest(`/auditor/ai-drafts/${encodeURIComponent(id)}/reject`, { method: "POST" });
}

export function editAiDraft(id: string, title: string, body: string): Promise<AiDraft> {
  return apiRequest(`/auditor/ai-drafts/${encodeURIComponent(id)}`, { method: "PUT", body: JSON.stringify({ title, body }) });
}
