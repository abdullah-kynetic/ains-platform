import { USE_MOCKS } from "../api";
import { getWorkspace } from "../workflow-api";
import { delay, readStore } from "../mock/store";
import { seedDocuments } from "../mock/seed";
import type { EngagementDocument } from "./types";

// The assigned-auditor workspace is the existing server-authorized document source.
export async function listDocuments(engagementId: string): Promise<EngagementDocument[]> {
  if (!USE_MOCKS) {
    const workspace = await getWorkspace(engagementId);
    const feedback: Record<string, string> = {
      unreadable: "Please replace with a readable copy.",
      wrong_document: "Please provide the requested document.",
      wrong_period: "Please provide the review-period document.",
      missing_pages: "Please provide a complete copy.",
    };
    return workspace.requests.flatMap((request) => request.documents.map((document) => ({
      id: document.id, engagementId, requestId: request.requestId, name: document.name,
      sha256: document.sha256, uploadedAt: document.uploadedAt,
      // This endpoint does not return a page count or uploader identity. Never invent either.
      pages: null, uploadedBy: null,
      feedback: document.feedbackCode ? feedback[document.feedbackCode] ?? "Document needs review." : null,
    })));
  }
  return delay(readStore("kien-mock-docs-v1", seedDocuments).filter((d) => d.engagementId === engagementId));
}
