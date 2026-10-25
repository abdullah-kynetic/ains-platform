import catalog from "../../.generated/catalog.json";
import { apiRequest, USE_MOCKS } from "./api";
import { cloneMockEngagement, saveMockEngagement, invalidateMockDecision } from "./mock-data";

export type Assessment = "supported" | "partial" | "conflicting" | "unable_to_determine";
export type Decision = { applicability: "applicable" | "not_applicable"; assessment: Assessment | null; notes: string };
export type ManualRequest = { id: string; requestId: string; title: string; restricted: boolean; stage: string; applicable: boolean; followUp: boolean; naReviewState: string | null; representation: string | null; applicability: Decision["applicability"] | null; assessment: Assessment | null; notes: string; documents: { id: string; name: string; sha256: string; version: string; uploadedAt: string; feedbackCode?: string | null }[] };
export type Readiness = { ready: boolean; reviewed: number; total: number; blockers: string[]; meaning: string };
export type History = { id: string; actor: string; action: string; entityId: string; at: string; details: Record<string, unknown> };
export type Workspace = { id: string; firmName: string; requests: ManualRequest[]; readiness: Readiness; history: History[] };
export type ClientSummary = { id: string; firmId?: string; firmName: string; status: string; readiness: Readiness };
export type WorkspaceInput = { firmName: string; reviewPeriodStart: string; reviewPeriodEnd: string; dueDate: string | null };
export type CreatedWorkspace = { id: string; firmId: string; firmName: string; slug: string; status: string; requestCount: number; clientAccessProvisioned: boolean };
export type PipelineStage = "intake" | "document_collection" | "auditor_review" | "report_drafting" | "awaiting_signature" | "complete";
export type PipelineEngagement = { id: string; firm: string; stage: PipelineStage; due: string | null; assignee: string; progress: number; blockers: number; nextAction: string; reportSigned: boolean };
export type TaskPriority = "high" | "normal" | "low";
export type AuditorTask = { id: string; engagementId: string; title: string; requestId: string | null; due: string | null; priority: TaskPriority; assignee: string; completed: boolean };
export type TaskInput = { title: string; requestId: string | null; due: string | null; priority: TaskPriority };
export type ActivityKind = "upload" | "review" | "feedback" | "questionnaire";
export type AuditorActivity = { id: string; kind: ActivityKind; actor: string; action: string; subject: string; context: string; occurredAt: string; engagementId: string };
type MockState = { decisions: Record<string, Decision>; history: History[] };
const key = "ains-synthetic-auditor-v1";
const pipelineKey = "ains-synthetic-pipeline-v1";
const tasksKey = "ains-synthetic-tasks-v2";
const workspacesKey = "ains-synthetic-workspaces-v1";
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
  const created = JSON.parse(localStorage.getItem(workspacesKey) ?? "[]") as CreatedWorkspace[];
  return [
    { id: data.id, firmName: data.firmName, status: "collecting", readiness: workspace.readiness },
    ...created.map((entry) => ({ id: entry.id, firmName: entry.firmName, status: entry.status, readiness: { ready: false, reviewed: 0, total: 34, blockers: ["Initial engagement setup required"], meaning: "Ready for human report drafting, not a clean opinion or signed report." } })),
  ];
}

export async function createClientWorkspace(input: WorkspaceInput): Promise<CreatedWorkspace> {
  if (!USE_MOCKS) {
    return apiRequest("/auditor/workspaces", {
      method: "POST",
      body: JSON.stringify({ firm_name: input.firmName, review_period_start: input.reviewPeriodStart, review_period_end: input.reviewPeriodEnd, due_date: input.dueDate }),
    });
  }
  const existing = JSON.parse(localStorage.getItem(workspacesKey) ?? "[]") as CreatedWorkspace[];
  const base = input.firmName.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "").slice(0, 80) || "client";
  let slug = base; let suffix = 2;
  while (existing.some((entry) => entry.slug === slug)) slug = `${base}-${suffix++}`;
  const created: CreatedWorkspace = { id: crypto.randomUUID(), firmId: crypto.randomUUID(), firmName: input.firmName.trim(), slug, status: "draft", requestCount: 34, clientAccessProvisioned: false };
  localStorage.setItem(workspacesKey, JSON.stringify([...existing, created]));
  return created;
}

const syntheticPipeline: PipelineEngagement[] = [
  { id: "eng-synthetic-002", firm: "Northstar Brokerage Inc. (synthetic)", stage: "intake", due: "2026-12-18", assignee: "Quentin", progress: 8, blockers: 0, nextAction: "Confirm review period and applicable business lines", reportSigned: false },
  { id: "eng-synthetic-001", firm: "Example Securities LLC (synthetic)", stage: "document_collection", due: "2026-12-15", assignee: "Quentin", progress: 41, blockers: 2, nextAction: "Receive two replacement documents", reportSigned: false },
  { id: "eng-synthetic-003", firm: "Meridian Capital Markets (synthetic)", stage: "document_collection", due: "2026-12-22", assignee: "Quentin", progress: 56, blockers: 1, nextAction: "Complete remaining questionnaire representations", reportSigned: false },
  { id: "eng-synthetic-004", firm: "Harborview Securities (synthetic)", stage: "auditor_review", due: "2026-11-26", assignee: "Quentin", progress: 74, blockers: 3, nextAction: "Resolve three evidence assessments", reportSigned: false },
  { id: "eng-synthetic-005", firm: "Summit BD Partners (synthetic)", stage: "report_drafting", due: "2026-11-14", assignee: "Quentin", progress: 88, blockers: 0, nextAction: "Prepare draft for credentialed auditor review", reportSigned: false },
  { id: "eng-synthetic-006", firm: "Cedar Ridge Financial (synthetic)", stage: "awaiting_signature", due: "2026-11-08", assignee: "Quentin", progress: 97, blockers: 0, nextAction: "Quentin reviews and explicitly signs the report", reportSigned: false },
  { id: "eng-synthetic-007", firm: "Bluewater Securities Group (synthetic)", stage: "complete", due: "2026-10-17", assignee: "Quentin", progress: 100, blockers: 0, nextAction: "No open action", reportSigned: true },
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
  { id: "task-review-program", engagementId: "eng-synthetic-001", title: "Review newly uploaded program evidence", requestId: "AML-BD-001", due: "2026-10-22", priority: "high", assignee: "Quentin", completed: false },
  { id: "task-missing-pages", engagementId: "eng-synthetic-001", title: "Check replacement for missing pages", requestId: "AML-BD-009", due: "2026-10-23", priority: "high", assignee: "Quentin", completed: false },
  { id: "task-applicability", engagementId: "eng-synthetic-001", title: "Resolve applicability representation", requestId: "AML-BD-026", due: "2026-11-05", priority: "normal", assignee: "Quentin", completed: false },
  { id: "task-status-update", engagementId: "eng-synthetic-001", title: "Prepare engagement status update", requestId: "Example Securities LLC", due: "2026-11-07", priority: "low", assignee: "Quentin", completed: false },
];

export async function getAuditorTasks(): Promise<AuditorTask[]> {
  if (!USE_MOCKS) return apiRequest("/auditor/tasks");
  return JSON.parse(localStorage.getItem(tasksKey) ?? JSON.stringify(syntheticTasks)) as AuditorTask[];
}

function saveSyntheticTasks(tasks: AuditorTask[]) {
  localStorage.setItem(tasksKey, JSON.stringify(tasks));
}

export async function createAuditorTask(engagementId: string, input: TaskInput): Promise<AuditorTask> {
  if (!USE_MOCKS) {
    return apiRequest(`/auditor/engagements/${encodeURIComponent(engagementId)}/tasks`, {
      method: "POST",
      body: JSON.stringify({ title: input.title, request_id: input.requestId, due_date: input.due, priority: input.priority }),
    });
  }
  const task: AuditorTask = { id: crypto.randomUUID(), engagementId, ...input, assignee: "Quentin", completed: false };
  saveSyntheticTasks([...(await getAuditorTasks()), task]);
  return task;
}

export async function updateAuditorTask(id: string, changes: Partial<TaskInput> & { completed?: boolean }): Promise<AuditorTask> {
  if (!USE_MOCKS) {
    return apiRequest(`/auditor/tasks/${encodeURIComponent(id)}`, {
      method: "PATCH",
      body: JSON.stringify({
        ...(changes.title !== undefined ? { title: changes.title } : {}),
        ...(changes.requestId !== undefined ? { request_id: changes.requestId } : {}),
        ...(changes.due !== undefined ? { due_date: changes.due } : {}),
        ...(changes.priority !== undefined ? { priority: changes.priority } : {}),
        ...(changes.completed !== undefined ? { completed: changes.completed } : {}),
      }),
    });
  }
  const tasks = await getAuditorTasks();
  const current = tasks.find((task) => task.id === id);
  if (!current) throw new Error("Task not found.");
  const updated = { ...current, ...changes };
  saveSyntheticTasks(tasks.map((task) => task.id === id ? updated : task));
  return updated;
}

export async function setAuditorTaskCompletion(id: string, completed: boolean): Promise<void> {
  await updateAuditorTask(id, { completed });
}

export async function getAuditorActivity(): Promise<AuditorActivity[]> {
  if (!USE_MOCKS) return apiRequest("/auditor/activity");
  const ago = (minutes: number) => new Date(Date.now() - minutes * 60_000).toISOString();
  return [
    { id: "activity-upload-001", kind: "upload", actor: "Example Securities LLC", action: "uploaded new evidence for", subject: "AML-BD-001", context: "Evidence received for storage verification · Synthetic file", occurredAt: ago(12), engagementId: "eng-synthetic-001" },
    { id: "activity-review-001", kind: "review", actor: "Synthetic Auditor", action: "recorded a human assessment for", subject: "AML-BD-018", context: "Internal auditor decision recorded", occurredAt: ago(38), engagementId: "eng-synthetic-001" },
    { id: "activity-feedback-001", kind: "feedback", actor: "Synthetic Auditor", action: "sent document-level feedback for", subject: "AML-BD-009", context: "Client feedback contains intake issues only", occurredAt: ago(60), engagementId: "eng-synthetic-001" },
    { id: "activity-questionnaire-001", kind: "questionnaire", actor: "Example Securities LLC", action: "updated a representation for", subject: "AML-BD-026", context: "Response is waiting for human review", occurredAt: ago(24 * 60), engagementId: "eng-synthetic-001" },
  ];
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
