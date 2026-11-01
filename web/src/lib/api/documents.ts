import { delay, readStore } from "../mock/store";
import { seedDocuments } from "../mock/seed";
import type { EngagementDocument } from "./types";

// TODO(backend): GET /auditor/engagements/{id}/documents -> EngagementDocument[] (hashes from storage receipts)
export async function listDocuments(engagementId: string): Promise<EngagementDocument[]> {
  return delay(readStore("kien-mock-docs-v1", seedDocuments).filter((d) => d.engagementId === engagementId));
}
