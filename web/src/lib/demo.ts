/** Browser-only synthetic workflow. Never grants a backend session or sends files. */
import catalog from "./demo-catalog.json";
import type { Engagement, ClientStatus } from "./checklist";
import type { AuditorFinding, AuditorQueueItem, ManagedEngagement, Questionnaire } from "./api";

const demoId = "eng-synthetic-001";
const firmName = "Example Securities LLC (synthetic)";
const records: ManagedEngagement[] = [{
  id: demoId, firmId: "synthetic-firm", firmName, status: "collecting",
  checklistVersion: catalog.version, itemCount: catalog.items.length,
}];
const followUps = new Set<string>();
const uploaded = new Map<string, { name: string; size: number; uploadedAt: string }>();
const answers = new Map<string, boolean>();
const naDecisions = new Map<string, "approved" | "rejected">();
const queue: AuditorQueueItem[] = [{
  firmName, engagementId: demoId, itemId: "AML-BD-003", itemTitle: "AML training records",
  clientStatus: "with_auditor", naReviewState: null,
  evidence: [{
    id: "synthetic-evidence-1", name: "synthetic-training-record.txt",
    egnytePath: "/Shared/AINS-Dev/synthetic/example/AML-BD-003/synthetic-training-record.txt",
    sha256: "0".repeat(64), version: "synthetic-v1",
    checks: [{ id: "synthetic-check-1", checkType: "readable", status: "passed",
      details: { synthetic: true }, citations: [], durationMs: 25 }],
  }],
  findings: [{
    id: "synthetic-finding-1", title: "Synthetic training follow-up",
    body: "This fictional training record requires auditor review before a conclusion can be reached.",
    severity: "low", reviewState: "pending",
    citations: [{ page: 1, quote: "Synthetic training completion record for auditor review." }],
  }],
}];

function questions(id: string): Questionnaire {
  return { engagementId: id, questions: catalog.items.filter((item) => item.condition_question).map((item) => ({
    itemId: item.id, sectionTitle: catalog.sections.find((section) => section.id === item.section)!.title,
    question: item.condition_question!, answer: answers.get(item.id) ?? null,
    naReviewState: naDecisions.get(item.id) ?? (answers.get(item.id) === false ? "pending" : null),
    negativeAnswerInstruction: item.negative_answer_instruction,
  })) };
}

export function demoEngagement(): Engagement {
  return {
    id: demoId, firmName, engagementType: "FINRA Rule 3310 Independent AML Test",
    reviewPeriod: { start: "2025-01-01", end: "2025-12-31" }, dueDate: "2026-12-15",
    sections: catalog.sections.map((section) => ({ ...section, items: catalog.items
      .filter((item) => item.section === section.id)
      .filter((item) => item.intake_stage !== "auditor_follow_up" || followUps.has(`${demoId}/${item.id}`))
      .filter((item) => naDecisions.get(item.id) !== "approved")
      .filter((item) => answers.get(item.id) !== false || item.negative_answer_instruction)
      .map((item) => {
        const file = uploaded.get(item.id);
        const status: ClientStatus = item.restricted ? "restricted_do_not_upload"
          : file ? "checking" : item.id === "AML-BD-003" ? "with_auditor" : "requested";
        return { id: item.id, title: item.title, description: item.description, status,
          reason: answers.get(item.id) === false ? item.negative_answer_instruction ?? undefined : undefined,
          files: file ? [{ id: `synthetic-${item.id}`, ...file }] : [] };
      }) })),
  };
}

export function demoUpload(itemId: string, file: File) {
  const item = catalog.items.find((item) => item.id === itemId);
  if (!item || item.restricted) throw new Error("This item cannot accept demo uploads.");
  // Retain metadata only. File bytes are never read or transmitted.
  uploaded.set(itemId, { name: file.name, size: file.size, uploadedAt: new Date().toISOString() });
}

export function demoQuestionnaire(id: string) { return structuredClone(questions(id)); }
export function demoAnswers(id: string, values: Array<{ itemId: string; applies: boolean }>) {
  for (const value of values) {
    answers.set(value.itemId, value.applies); naDecisions.delete(value.itemId);
  }
  return demoQuestionnaire(id);
}

export async function demoRequest<T>(path: string, init: RequestInit): Promise<T> {
  const body = init.body ? JSON.parse(String(init.body)) : {};
  const parts = path.split("/").filter(Boolean).map(decodeURIComponent);
  let result: unknown;
  if (path === "/auditor/queue") {
    const naItems: AuditorQueueItem[] = questions(demoId).questions.filter((q) => q.naReviewState === "pending").map((q) => ({
      firmName, engagementId: demoId, itemId: q.itemId, itemTitle: catalog.items.find((i) => i.id === q.itemId)!.title,
      clientStatus: "with_auditor", naReviewState: "pending", evidence: [], findings: [],
    }));
    result = [...queue, ...naItems];
  } else if (parts[1] === "findings") {
    const finding = queue.flatMap((item) => item.findings).find((f) => f.id === parts[2]);
    if (!finding) throw new Error("Synthetic finding not found.");
    if (body.body) finding.body = body.body;
    if (body.severity) finding.severity = body.severity;
    finding.reviewState = ({ accept: "accepted", edit: "edited", reject: "rejected" } as const)[body.action as "accept" | "edit" | "reject"];
    result = finding;
  } else if (parts.includes("na-review")) {
    const itemId = parts[4];
    const definition = catalog.items.find((item) => item.id === itemId);
    if (body.decision === "approve" && definition?.negative_answer_requires_representation &&
      (!uploaded.has(itemId) || !body.representationReviewed)) {
      throw new Error("Upload a synthetic representation and confirm its review first.");
    }
    naDecisions.set(itemId, body.decision === "approve" ? "approved" : "rejected");
    if (body.decision === "reject") answers.set(itemId, true);
    result = questions(demoId).questions.find((q) => q.itemId === itemId);
  } else if (path === "/auditor/engagements") {
    if (init.method === "POST") {
      const record: ManagedEngagement = { id: crypto.randomUUID(), firmId: crypto.randomUUID(),
        firmName: body.firmName, status: "draft", checklistVersion: catalog.version, itemCount: 34 };
      records.push(record); result = record;
    } else result = records;
  } else if (parts[1] === "engagements") {
    const record = records.find((item) => item.id === parts[2]);
    if (!record) throw new Error("Synthetic engagement not found.");
    if (parts[3] === "publish") { record.status = "collecting"; result = record; }
    else if (parts[3] === "checklist") result = {
      engagement: record, catalog,
      followUps: catalog.items.filter((item) => item.intake_stage === "auditor_follow_up")
        .map((item) => ({ id: item.id, title: item.title, released: followUps.has(`${record.id}/${item.id}`) })),
    };
    else if (parts[5] === "release") { followUps.add(`${record.id}/${parts[4]}`); result = { status: "released" }; }
    else throw new Error("This action is not available in the synthetic demo.");
  } else throw new Error("This action requires the real backend.");
  return structuredClone(result) as T;
}

export type DemoFinding = AuditorFinding;
