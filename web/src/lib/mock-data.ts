import catalog from "../../.generated/catalog.json";
import type { Engagement } from "./checklist";

export const MOCK_ENGAGEMENT: Engagement = {
  id: "eng-synthetic-001",
  firmName: "Example Securities LLC (synthetic)",
  engagementType: "FINRA Rule 3310 Independent AML Test",
  reviewPeriod: { start: "2025-01-01", end: "2025-12-31" },
  dueDate: "2026-12-15",
  sections: catalog.sections.map((section) => ({
    ...section,
    items: catalog.requests.filter((request) => request.section === section.id && request.stage === "initial").map((request) => ({
      id: request.id, requestId: request.id,
      title: request.title, description: request.client_description,
      restricted: request.restricted, allowedEvidenceTypes: request.allowed_evidence_types,
      status: request.restricted ? "restricted_do_not_upload" as const : "requested" as const,
      files: [],
    })),
  })),
};

export function cloneMockEngagement(): Engagement {
  if (typeof window !== "undefined") {
    const saved = localStorage.getItem("ains-synthetic-engagement-v1");
    if (saved) return JSON.parse(saved) as Engagement;
  }
  return structuredClone(MOCK_ENGAGEMENT);
}

export function saveMockEngagement(data: Engagement): void {
  localStorage.setItem("ains-synthetic-engagement-v1", JSON.stringify(data));
}
