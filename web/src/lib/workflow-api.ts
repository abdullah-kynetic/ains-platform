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
export type PipelineStage = "intake" | "document_collection" | "auditor_review" | "report_drafting" | "awaiting_signature" | "complete";
export type PipelineEngagement = { id: string; firm: string; stage: PipelineStage; due: string | null; assignee: string; progress: number; blockers: number; nextAction: string; reportSigned: boolean };
export type TaskPriority = "high" | "normal" | "low";
export type AuditorTask = { id: string; engagementId: string; title: string; requestId: string | null; due: string | null; priority: TaskPriority; assignee: string; completed: boolean };
type MockState = { decisions: Record<string, Decision>; history: History[] };
const key = "ains-synthetic-auditor-v1";
const pipelineKey = "ains-synthetic-pipeline-v1";
const tasksKey = "ains-synthetic-tasks-v1";
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

const syntheticPipeline: PipelineEngagement[] = [
  { id: "eng-synthetic-002", firm: "Northstar Brokerage Inc. (synthetic)", stage: "intake", due: "2026-12-18", assignee: "Quinton", progress: 8, blockers: 0, nextAction: "Confirm review period and applicable business lines", reportSigned: false },
  { id: "eng-synthetic-001", firm: "Example Securities LLC (synthetic)", stage: "document_collection", due: "2026-12-15", assignee: "Quinton", progress: 41, blockers: 2, nextAction: "Receive two replacement documents", reportSigned: false },
  { id: "eng-synthetic-003", firm: "Meridian Capital Markets (synthetic)", stage: "document_collection", due: "2026-12-22", assignee: "Quinton", progress: 56, blockers: 1, nextAction: "Complete remaining questionnaire representations", reportSigned: false },
  { id: "eng-synthetic-004", firm: "Harborview Securities (synthetic)", stage: "auditor_review", due: "2026-11-26", assignee: "Quinton", progress: 74, blockers: 3, nextAction: "Resolve three evidence assessments", reportSigned: false },
  { id: "eng-synthetic-005", firm: "Summit BD Partners (synthetic)", stage: "report_drafting", due: "2026-11-14", assignee: "Quinton", progress: 88, blockers: 0, nextAction: "Prepare draft for credentialed auditor review", reportSigned: false },
  { id: "eng-synthetic-006", firm: "Cedar Ridge Financial (synthetic)", stage: "awaiting_signature", due: "2026-11-08", assignee: "Quinton", progress: 97, blockers: 0, nextAction: "Quinton reviews and explicitly signs the report", reportSigned: false },
  { id: "eng-synthetic-007", firm: "Bluewater Securities Group (synthetic)", stage: "complete", due: "2026-10-17", assignee: "Quinton", progress: 100, blockers: 0, nextAction: "No open action", reportSigned: true },
];

export async function getPipeline(): Promise<PipelineEngagement[]> {
  if (!USE_MOCKS) return apiRequest("/auditor/pipeline");
  const stages = JSON.parse(localStorage.getItem(pipelineKey) ?? "{}") as Record<string, PipelineStage>;
  return syntheticPipeline.map((entry) => ({ ...entry, stage: stages[entry.id] ?? entry.stage }));
}

export async function movePipelineStage(id: string, stage: PipelineStage): Promise<void> {
  if (stage === "complete") throw new Error("Completion requires a separately recorded signed-report action.");
  if (!USE_MOCKS) {
    await apiRequest(`/auditor/engagements/${encodeURIComponent(id)}/pipeline-stage`, { method: "PATCH", body: JSON.stringify({ stage }) });
    return;
  }
  const stages = JSON.parse(localStorage.getItem(pipelineKey) ?? "{}") as Record<string, PipelineStage>;
  stages[id] = stage;
  localStorage.setItem(pipelineKey, JSON.stringify(stages));
}

const syntheticTasks: AuditorTask[] = [
  { id: "task-review-program", engagementId: "eng-synthetic-001", title: "Review newly uploaded program evidence", requestId: "AML-BD-001", due: "2026-10-22", priority: "high", assignee: "Quinton", completed: false },
  { id: "task-missing-pages", engagementId: "eng-synthetic-001", title: "Check replacement for missing pages", requestId: "AML-BD-009", due: "2026-10-23", priority: "high", assignee: "Quinton", completed: false },
  { id: "task-applicability", engagementId: "eng-synthetic-001", title: "Resolve applicability representation", requestId: "AML-BD-026", due: "2026-11-05", priority: "normal", assignee: "Quinton", completed: false },
  { id: "task-status-update", engagementId: "eng-synthetic-001", title: "Prepare engagement status update", requestId: "Example Securities LLC", due: "2026-11-07", priority: "low", assignee: "Quinton", completed: false },
];

export async function getAuditorTasks(): Promise<AuditorTask[]> {
  if (!USE_MOCKS) return apiRequest("/auditor/tasks");
  const completion = JSON.parse(localStorage.getItem(tasksKey) ?? "{}") as Record<string, boolean>;
  return syntheticTasks.map((task) => ({ ...task, completed: completion[task.id] ?? task.completed }));
}

export async function setAuditorTaskCompletion(id: string, completed: boolean): Promise<void> {
  if (!USE_MOCKS) {
    await apiRequest(`/auditor/tasks/${encodeURIComponent(id)}`, { method: "PATCH", body: JSON.stringify({ completed }) });
    return;
  }
  const completion = JSON.parse(localStorage.getItem(tasksKey) ?? "{}") as Record<string, boolean>;
  completion[id] = completed;
  localStorage.setItem(tasksKey, JSON.stringify(completion));
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
