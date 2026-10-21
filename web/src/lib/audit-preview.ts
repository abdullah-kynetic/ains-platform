/** Frontend review model and synthetic adapter; no inference or client evidence is loaded. */
import catalog from "./demo-catalog.json";
import { listManagedEngagements, USE_MOCKS } from "./api";
import { demoEngagement, demoSetClientDecision } from "./demo";

export type ProcessingState = "requested" | "queued" | "processing" | "review" | "complete" | "restricted" | "follow_up";
export type ReviewDecision = "sufficient" | "more_needed" | "not_applicable";
export type Correction = { decision: ReviewDecision; reason: string; tag: string; at: string };
export type ReviewDocument = {
  id: string; title: string; description: string; section: string;
  state: ProcessingState; fileName: string | null;
  stage: string; elapsedSeconds: number | null; summary: string | null;
  assessment: string | null; citations: Array<{ page: number; quote: string }>;
  corrections: Correction[];
};
export type AuditWorkspaceData = {
  engagementId: string; firmName: string;
  reviewPeriod: { start: string; end: string }; documents: ReviewDocument[];
};

/** Replace this interface with an authenticated backend adapter when integrations are in scope. */
export interface AuditWorkspaceSource {
  load(engagementId: string): Promise<AuditWorkspaceData>;
  review(engagementId: string, itemId: string, correction: Omit<Correction, "at">): Promise<void>;
}

const workspaces = new Map<string, AuditWorkspaceData>();
function requireDemo() {
  if (!USE_MOCKS) throw new Error("The analysis preview requires synthetic demo mode.");
}

export const syntheticAuditSource: AuditWorkspaceSource = {
  async load(engagementId) {
    requireDemo();
    if (!workspaces.has(engagementId)) {
      const record = (await listManagedEngagements()).find((item) => item.id === engagementId);
      if (!record) throw new Error("Synthetic engagement not found.");
      const seeded = engagementId === "eng-synthetic-001";
      workspaces.set(engagementId, {
        engagementId, firmName: record.firmName,
        reviewPeriod: { start: "2025-01-01", end: "2025-12-31" },
        documents: catalog.items.map((item, index) => {
          const number = index + 1;
          const state: ProcessingState = item.restricted ? "restricted" : number === 9 ? "follow_up"
            : seeded && number === 1 ? "complete" : seeded && [2, 3].includes(number) ? "review"
            : seeded && number === 7 ? "processing" : seeded && number === 8 ? "queued" : "requested";
          const analyzed = ["review", "complete"].includes(state);
          return {
            id: item.id, title: item.title, description: item.description,
            section: catalog.sections.find((section) => section.id === item.section)!.title,
            state, fileName: ["review", "complete", "queued", "processing"].includes(state) ? `synthetic-${item.id.toLowerCase()}.txt` : null,
            stage: state === "processing" ? "Extracting document text" : state === "queued" ? "Waiting for analysis" : analyzed ? "Analysis complete" : "Not started",
            elapsedSeconds: state === "processing" ? 42 : analyzed ? 76 : null,
            summary: analyzed ? `A fictional ${item.title.toLowerCase()} provided for this interface demonstration. No real document has been analyzed.` : null,
            assessment: analyzed ? "The synthetic evidence is ready for auditor review. Confirm the requested coverage and supporting records before deciding sufficiency." : null,
            citations: analyzed ? [{ page: 1, quote: `Synthetic evidence for ${item.id}; review period 2025-01-01 through 2025-12-31.` }] : [],
            corrections: seeded && number === 1 ? [{ decision: "sufficient", reason: "Synthetic auditor verified the requested coverage.", tag: "coverage_verified", at: "2026-10-20T12:00:00Z" }] : [],
          };
        }),
      });
    }
    if (engagementId === "eng-synthetic-001") {
      const clientItems = demoEngagement().sections.flatMap((section) => section.items);
      for (const item of workspaces.get(engagementId)!.documents) {
        const clientItem = clientItems.find((entry) => entry.id === item.id);
        if (item.state === "requested" && !item.summary && clientItem?.files.length) {
          item.state = "queued"; item.stage = "Waiting for analysis";
          item.fileName = clientItem.files.at(-1)!.name;
        }
        if (item.state === "follow_up" && clientItem) item.state = "requested";
      }
    }
    return structuredClone(workspaces.get(engagementId)!);
  },
  async review(engagementId, itemId, correction) {
    requireDemo();
    const document = workspaces.get(engagementId)?.documents.find((item) => item.id === itemId);
    if (!document || !["review", "complete"].includes(document.state)) throw new Error("This document is not ready for review.");
    if (correction.reason.trim().length < 10) throw new Error("Explain the review decision in at least 10 characters.");
    document.corrections.push({ ...correction, at: new Date().toISOString() });
    document.state = correction.decision === "more_needed" ? "requested" : "complete";
    if (engagementId === "eng-synthetic-001") {
      demoSetClientDecision(itemId, correction.decision === "more_needed" ? "action_needed_more" : "accepted_for_testing",
        correction.decision === "more_needed" ? "Additional supporting documents are needed. Please contact the auditor." : undefined);
    }
  },
};

export function reportReadiness(documents: ReviewDocument[]) {
  const relevant = documents.filter((item) => !["restricted", "follow_up"].includes(item.state));
  const completed = relevant.filter((item) => item.state === "complete").length;
  return { completed, total: relevant.length, unresolved: relevant.filter((item) => item.state !== "complete"),
    restricted: documents.filter((item) => item.state === "restricted"),
    followUps: documents.filter((item) => item.state === "follow_up") };
}
