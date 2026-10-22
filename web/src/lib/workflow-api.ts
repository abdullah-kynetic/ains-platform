import catalog from "../../.generated/catalog.json";
import { apiRequest, USE_MOCKS } from "./api";
import { cloneMockEngagement, saveMockEngagement, invalidateMockDecision } from "./mock-data";

export type Assessment = "supported" | "partial" | "conflicting" | "unable_to_determine";
export type Decision = { applicability: "applicable" | "not_applicable"; assessment: Assessment | null; notes: string };
export type ManualRequest = { id: string; requestId: string; title: string; restricted: boolean; stage: string; applicable: boolean; followUp: boolean; naReviewState: string | null; representation: string | null; applicability: Decision["applicability"] | null; assessment: Assessment | null; notes: string; documents: { id: string; name: string; sha256: string; version: string; uploadedAt: string; feedbackCode?: string | null }[] };
export type Readiness = { ready: boolean; reviewed: number; total: number; blockers: string[]; meaning: string };
export type History = { id: string; actor: string; action: string; entityId: string; at: string; details: Record<string, unknown> };
export type Workspace = { id: string; firmName: string; requests: ManualRequest[]; readiness: Readiness; history: History[] };
export type ClientSummary = { id: string; firmName: string; status: string; readiness: Readiness };
type MockState = { decisions: Record<string, Decision>; history: History[] };
const key = "ains-synthetic-auditor-v1";
function mockState(): MockState { return JSON.parse(localStorage.getItem(key) ?? '{"decisions":{},"history":[]}'); }
function event(state: MockState, action: string, entityId: string, before: unknown, after: unknown) {
  state.history.push({ id: crypto.randomUUID(), actor: "Synthetic Auditor", action, entityId, at: new Date().toISOString(), details: { before, after } });
  localStorage.setItem(key, JSON.stringify(state));
}

export async function getWorkspace(id: string): Promise<Workspace> {
  if (!USE_MOCKS) return apiRequest(`/auditor/engagements/${encodeURIComponent(id)}/workspace`);
  const data = cloneMockEngagement(); const state = mockState();
  const requests = catalog.requests.map((definition): ManualRequest => {
    const item = data.sections.flatMap((section) => section.items).find((item) => item.id === definition.id);
    const decision = state.decisions[definition.id];
    return { id: definition.id, requestId: definition.id, title: definition.title, restricted: definition.restricted,
      stage: definition.stage, applicable: item?.canUpload !== false, followUp: item?.followUp ?? false,
      naReviewState: item?.naReviewState ?? null, representation: item?.representation ?? null,
      applicability: decision?.applicability ?? null, assessment: decision?.assessment ?? null, notes: decision?.notes ?? "",
      documents: (item?.files ?? []).map((file) => ({ ...file, sha256: file.sha256 ?? "", version: "synthetic-1" })) };
  });
  const blockers = requests.flatMap((request) => [
    ...(!request.applicability ? [`${request.requestId}: applicability undecided`] : []),
    ...(request.applicability === "applicable" && !request.assessment ? [`${request.requestId}: assessment undecided`] : []),
    ...(request.naReviewState === "pending" ? [`${request.requestId}: client representation awaits review`] : []),
    ...(request.applicability === "applicable" && data.sections.flatMap((section) => section.items).find((item) => item.id === request.id)?.status.startsWith("action_needed") ? [`${request.requestId}: replacement requested`] : []),
  ]);
  return { id: data.id, firmName: data.firmName, requests, history: state.history,
    readiness: { ready: !blockers.length, reviewed: requests.filter((request) => request.applicability && (request.applicability === "not_applicable" || request.assessment)).length,
      total: 34, blockers, meaning: "Ready for human report drafting, not a clean opinion or signed report." } };
}

export async function getClients(): Promise<ClientSummary[]> {
  if (!USE_MOCKS) return apiRequest("/auditor/engagements");
  const data = cloneMockEngagement(); const workspace = await getWorkspace(data.id);
  return [{ id: data.id, firmName: data.firmName, status: "collecting", readiness: workspace.readiness }];
}

export async function saveDecision(id: string, itemId: string, decision: Decision): Promise<void> {
  if (!USE_MOCKS) return apiRequest(`/auditor/engagements/${id}/items/${itemId}/decision`, { method: "PATCH", body: JSON.stringify(decision) });
  if ((decision.applicability === "not_applicable" || decision.assessment !== "supported") && !decision.notes.trim()) throw new Error("Document the reason in internal notes.");
  const state = mockState(); const before = state.decisions[itemId] ?? null;
  state.decisions[itemId] = decision; event(state, "request.manual_decision", itemId, before, decision);
  const data = cloneMockEngagement(); const item = data.sections.flatMap((section) => section.items).find((item) => item.id === itemId);
  if (item) { item.canUpload = decision.applicability === "applicable"; item.naReviewState = item.canUpload ? null : "approved"; }
  saveMockEngagement(data);
}

export async function requestFollowUp(id: string, itemId: string): Promise<void> {
  if (!USE_MOCKS) return apiRequest(`/auditor/engagements/${id}/items/${itemId}/follow-up`, { method: "POST" });
  const definition = catalog.requests.find((request) => request.id === itemId)!;
  if (definition.restricted) throw new Error("Restricted requests cannot accept uploads.");
  const data = cloneMockEngagement(); const section = data.sections.find((section) => section.id === definition.section)!;
  let item = section.items.find((item) => item.id === itemId);
  if (!item) { item = { id: itemId, requestId: itemId, title: definition.title, description: definition.client_description, restricted: false, allowedEvidenceTypes: definition.allowed_evidence_types, status: "requested", files: [] }; section.items.push(item); }
  item.followUp = true; item.canUpload = true; item.status = "requested";
  item.naReviewState = null;
  invalidateMockDecision(itemId, true);
  saveMockEngagement(data); event(mockState(), "request.follow_up", itemId, null, { followUp: true });
}

export async function sendFeedback(id: string, itemId: string, documentId: string, code: string): Promise<void> {
  if (!USE_MOCKS) return apiRequest(`/auditor/engagements/${id}/items/${itemId}/feedback`, { method: "POST", body: JSON.stringify({ code, document_id: documentId }) });
  const reasons: Record<string, string> = { unreadable: "Please replace this file with a readable copy.", wrong_document: "Please provide the requested document.", wrong_period: "Please provide a file covering the review period.", missing_pages: "Please provide the missing pages.", usable: "" };
  const data = cloneMockEngagement(); const item = data.sections.flatMap((section) => section.items).find((item) => item.id === itemId)!;
  const file = item.files.find((file) => file.id === documentId)!;
  file.feedback = reasons[code]; item.reason = reasons[code]; item.status = code === "usable" ? "with_auditor" : "action_needed_reupload";
  invalidateMockDecision(itemId);
  saveMockEngagement(data); event(mockState(), "document.feedback", itemId, null, { documentId, code });
}
