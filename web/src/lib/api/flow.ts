/**
 * Quentin's checklist workflow (Lane 2 contract: docs/kb/23-workflow-api.md, route list in
 * docs/handoff/LANE-1-HANDOFF.md). Real routes when NEXT_PUBLIC_USE_MOCKS is off; a small
 * synthetic in-browser store otherwise, so the mock build and its browser tests still run.
 * Every field here is client-safe: no findings, internal notes or assessments.
 */
import { apiRequest, getEngagement, USE_MOCKS } from "../api";
import { delay, readStore, updateStore, uid } from "../mock/store";
import catalog from "../../../.generated/catalog.json";

export type Stage =
  | "not_sent" | "checklist_sent" | "client_working" | "under_review" | "info_requested"
  | "report_drafting" | "report_sent" | "confirmed" | "invoiced" | "paid";
export type ItemState = "not_started" | "submitted" | "needs_info" | "accepted" | "na" | "restricted";
export type IssueKind = "outdated" | "wrong_year" | "incorrect" | "missing";

export type NARequest = {
  state: "pending" | "accepted" | "rejected" | null;
  reason: string | null;
  decisionNote: string | null;
  requestedAt: string | null;
};
export type DocRef = { id: string; number: string | null; name: string; feedback?: string | null };
export type ProgressItem = {
  id: string;
  number: number;
  requestId: string;
  title: string;
  status: ItemState;
  openIssues: number;
  naRequest: NARequest | null;
  documents: DocRef[];
};
export type Progress = {
  engagementId: string;
  stage: Stage;
  checklistSentAt: string | null;
  clientSubmittedAt: string | null;
  reportConfirmedAt: string | null;
  counts: { total: number; notStarted: number; submitted: number; needsInfo: number; accepted: number; notApplicable: number; naPending: number };
  percentSubmitted: number;
  percentAccepted: number;
  items: ProgressItem[];
};
export type IssueMessage = { id: string; authorRole: "client" | "auditor"; body: string; documentNumber: string | null; createdAt: string };
export type Issue = {
  id: string;
  itemId: string;
  kind: IssueKind;
  status: "open" | "resolved";
  document: { id: string; number: string | null } | null;
  createdAt: string;
  resolvedAt: string | null;
  awaiting: "client" | "auditor" | null;
  messages: IssueMessage[];
};

export const STAGE_LABEL: Record<Stage, string> = {
  not_sent: "Checklist not sent",
  checklist_sent: "Checklist sent",
  client_working: "Client working",
  under_review: "Under review",
  info_requested: "Information requested",
  report_drafting: "Report drafting",
  report_sent: "Report sent",
  confirmed: "Report confirmed",
  invoiced: "Invoiced",
  paid: "Paid",
};
export const ITEM_LABEL: Record<ItemState, string> = {
  not_started: "Not started",
  submitted: "With auditor",
  needs_info: "Needs information",
  accepted: "Accepted for testing",
  na: "Does not apply",
  restricted: "Do not upload",
};
export const ISSUE_LABEL: Record<IssueKind, string> = {
  outdated: "Outdated",
  wrong_year: "Wrong year",
  incorrect: "Incorrect document",
  missing: "Missing document",
};

const e = encodeURIComponent;
const post = <T,>(path: string, body?: unknown) =>
  apiRequest<T>(path, { method: "POST", ...(body === undefined ? {} : { body: JSON.stringify(body) }) });

// --- step 2: dispatch and progress ------------------------------------------------------------

export async function sendChecklist(engagementId: string): Promise<{ sentAt: string; stage: Stage }> {
  if (!USE_MOCKS) return post(`/auditor/engagements/${e(engagementId)}/checklist/send`);
  const p = mutate(engagementId, (d) => { d.checklistSentAt = new Date().toISOString(); });
  return delay({ sentAt: p.checklistSentAt!, stage: p.stage });
}

export async function getProgress(engagementId: string, role: "auditor" | "client"): Promise<Progress> {
  if (!USE_MOCKS) return apiRequest(`${role === "auditor" ? "/auditor" : ""}/engagements/${e(engagementId)}/progress`);
  return delay(await withLegacyMock(derive(store(engagementId))));
}

/** Mock build only: reflect the older synthetic screens (questionnaire N/A, file feedback). */
async function withLegacyMock(progress: Progress): Promise<Progress> {
  const legacy = await getEngagement().catch(() => null);
  if (!legacy) return progress;
  const byId = new Map(legacy.sections.flatMap((s) => s.items).map((i) => [i.id, i]));
  for (const item of progress.items) {
    const old = byId.get(item.id);
    if (!old) continue;
    if (old.status === "not_applicable" && item.status !== "na") item.status = "na";
    for (const f of old.files) if (!item.documents.some((d) => d.id === f.id)) item.documents.push({ id: f.id, number: null, name: f.name, feedback: f.feedback ?? null });
  }
  return progress;
}

// --- step 3: reasoned N/A ---------------------------------------------------------------------

export async function requestNA(engagementId: string, itemId: string, reason: string): Promise<unknown> {
  if (!USE_MOCKS) return post(`/engagements/${e(engagementId)}/items/${e(itemId)}/na-request`, { reason });
  return delay(mutateItem(engagementId, itemId, (i) => { i.naRequest = { state: "pending", reason, decisionNote: null, requestedAt: new Date().toISOString() }; }));
}

export async function decideNA(engagementId: string, itemId: string, decision: "accept" | "reject", note?: string): Promise<unknown> {
  if (!USE_MOCKS) return post(`/auditor/engagements/${e(engagementId)}/items/${e(itemId)}/na-request/decision`, { decision, ...(note ? { note } : {}) });
  return delay(mutateItem(engagementId, itemId, (i) => {
    i.naRequest = { ...i.naRequest!, state: decision === "accept" ? "accepted" : "rejected", decisionNote: note ?? null };
    if (decision === "accept") i.status = "na";
  }));
}

// --- step 4: documents, mapping, submission ----------------------------------------------------

export async function linkDocument(engagementId: string, itemId: string, documentId: string, linked: boolean): Promise<unknown> {
  if (!USE_MOCKS) return apiRequest(`/engagements/${e(engagementId)}/items/${e(itemId)}/documents/${e(documentId)}/link`, { method: linked ? "POST" : "DELETE" });
  const doc = (await listEngagementDocuments()).find((d) => d.id === documentId);
  return delay(mutateItem(engagementId, itemId, (i) => {
    i.documents = i.documents.filter((d) => d.id !== documentId);
    if (linked && doc) i.documents.push(doc);
  }));
}

export async function submitItem(engagementId: string, itemId: string): Promise<unknown> {
  if (!USE_MOCKS) return post(`/engagements/${e(engagementId)}/items/${e(itemId)}/submit`);
  return delay(mutateItem(engagementId, itemId, (i) => { i.status = "submitted"; }));
}

/** `submitted` and `notReady` are request ids (for example "AML-BD-001"). */
export async function submitAll(engagementId: string): Promise<{ submitted: string[]; notReady: string[]; stage: Stage }> {
  if (!USE_MOCKS) return post(`/engagements/${e(engagementId)}/submit`);
  const submitted: string[] = [];
  const p = mutate(engagementId, (d) => {
    for (const i of d.items) if (i.status === "not_started" && i.documents.length && i.naRequest?.state !== "pending") { i.status = "submitted"; submitted.push(i.requestId); }
    d.clientSubmittedAt = new Date().toISOString();
  });
  return delay({ submitted, notReady: p.items.filter((i) => i.status === "not_started").map((i) => i.requestId), stage: p.stage });
}

export async function acceptItem(engagementId: string, itemId: string): Promise<unknown> {
  if (!USE_MOCKS) return post(`/auditor/engagements/${e(engagementId)}/items/${e(itemId)}/accept`);
  return delay(mutateItem(engagementId, itemId, (i) => { i.status = "accepted"; }));
}

/** Every document of the engagement (linked or not), numbered, for mapping to requests. */
export async function listEngagementDocuments(): Promise<DocRef[]> {
  const current = await getEngagement();
  const seen = new Map<string, DocRef>();
  const files = [...current.sections.flatMap((s) => s.items.flatMap((i) => i.files)), ...(current.unassignedDocuments ?? [])] as { id: string; name: string; number?: string | null; feedback?: string | null }[];
  files.forEach((f, index) => {
    // The mock build has no server numbering; give synthetic files a stable display number.
    const number = f.number ?? (USE_MOCKS ? `1.${index + 1}` : null);
    if (!seen.has(f.id)) seen.set(f.id, { id: f.id, number, name: f.name, feedback: f.feedback ?? null });
  });
  return [...seen.values()].sort((a, b) => docOrder(a.number) - docOrder(b.number));
}

const docOrder = (n: string | null) => (n ? Number(n.split(".")[1] ?? 0) : 1e9);

// --- step 5: issue flags and threads -----------------------------------------------------------

export async function listIssues(engagementId: string, role: "auditor" | "client"): Promise<Issue[]> {
  if (!USE_MOCKS) return apiRequest(`${role === "auditor" ? "/auditor" : ""}/engagements/${e(engagementId)}/issues`);
  return delay(store(engagementId).issues);
}

export async function flagIssue(engagementId: string, itemId: string, input: { kind: IssueKind; documentId?: string; note: string }): Promise<Issue> {
  if (!USE_MOCKS) return post(`/auditor/engagements/${e(engagementId)}/items/${e(itemId)}/issues`, input);
  let issue!: Issue;
  mutate(engagementId, (d) => {
    const doc = d.items.flatMap((i) => i.documents).find((x) => x.id === input.documentId);
    issue = { id: uid("iss"), itemId, kind: input.kind, status: "open", document: doc ? { id: doc.id, number: doc.number } : null, createdAt: new Date().toISOString(), resolvedAt: null, awaiting: "client", messages: [{ id: uid("msg"), authorRole: "auditor", body: input.note, documentNumber: null, createdAt: new Date().toISOString() }] };
    d.issues.push(issue);
    const item = d.items.find((i) => i.id === itemId);
    if (item) item.status = "needs_info";
  });
  return delay(issue);
}

export async function replyIssue(engagementId: string, issueId: string, role: "auditor" | "client", body: string, documentId?: string): Promise<Issue> {
  if (!USE_MOCKS) return post(`${role === "auditor" ? "/auditor" : ""}/engagements/${e(engagementId)}/issues/${e(issueId)}/replies`, { body, ...(documentId ? { documentId } : {}) });
  let issue!: Issue;
  mutate(engagementId, (d) => {
    issue = d.issues.find((i) => i.id === issueId)!;
    const doc = d.items.flatMap((i) => i.documents).find((x) => x.id === documentId);
    issue.messages.push({ id: uid("msg"), authorRole: role, body, documentNumber: doc?.number ?? null, createdAt: new Date().toISOString() });
    issue.awaiting = role === "client" ? "auditor" : "client";
  });
  return delay(issue);
}

export async function resolveIssue(engagementId: string, issueId: string, note?: string): Promise<Issue> {
  if (!USE_MOCKS) return post(`/auditor/engagements/${e(engagementId)}/issues/${e(issueId)}/resolve`, note ? { note } : {});
  let issue!: Issue;
  mutate(engagementId, (d) => {
    issue = d.issues.find((i) => i.id === issueId)!;
    issue.status = "resolved"; issue.awaiting = null; issue.resolvedAt = new Date().toISOString();
    const item = d.items.find((i) => i.id === issue.itemId);
    if (item && !d.issues.some((i) => i.itemId === item.id && i.status === "open")) item.status = "submitted";
  });
  return delay(issue);
}

// --- synthetic store (mock build only) ---------------------------------------------------------

type MockFlow = {
  checklistSentAt: string | null;
  clientSubmittedAt: string | null;
  items: ProgressItem[];
  issues: Issue[];
};

const key = (id: string) => `kien-mock-flow-v1-${id}`;
const seed = (): MockFlow => ({
  checklistSentAt: null,
  clientSubmittedAt: null,
  issues: [],
  items: catalog.requests.map((r, index) => ({ id: r.id, number: index + 1, requestId: r.id, title: r.title, status: "not_started" as ItemState, openIssues: 0, naRequest: null, documents: [] })),
});
const store = (id: string) => readStore(key(id), seed);

function derive(d: MockFlow): Progress {
  const items = d.items.map((i) => ({ ...i, openIssues: d.issues.filter((x) => x.itemId === i.id && x.status === "open").length }));
  const count = (s: ItemState) => items.filter((i) => i.status === s).length;
  const total = items.length - count("restricted");
  const stage: Stage = !d.checklistSentAt ? "not_sent"
    : d.issues.some((x) => x.status === "open") ? "info_requested"
    : count("submitted") + count("accepted") ? "under_review"
    : items.some((i) => i.documents.length || i.naRequest) ? "client_working" : "checklist_sent";
  return {
    engagementId: "mock",
    stage,
    checklistSentAt: d.checklistSentAt,
    clientSubmittedAt: d.clientSubmittedAt,
    reportConfirmedAt: null,
    counts: { total, notStarted: count("not_started"), submitted: count("submitted"), needsInfo: count("needs_info"), accepted: count("accepted"), notApplicable: count("na"), naPending: items.filter((i) => i.naRequest?.state === "pending").length },
    percentSubmitted: total ? Math.round(((count("submitted") + count("accepted") + count("na")) / total) * 100) : 0,
    percentAccepted: total ? Math.round(((count("accepted") + count("na")) / total) * 100) : 0,
    items: [...items].sort((a, b) => Number(a.status === "na") - Number(b.status === "na") || a.number - b.number),
  };
}

function mutate(id: string, change: (d: MockFlow) => void): Progress {
  return derive(updateStore(key(id), seed, change));
}

function mutateItem(id: string, itemId: string, change: (i: ProgressItem, all: MockFlow) => void): ProgressItem | undefined {
  const p = mutate(id, (d) => {
    const item = d.items.find((i) => i.id === itemId);
    if (item) change(item, d);
  });
  return p.items.find((i) => i.id === itemId);
}
