import { delay, readStore, updateStore } from "../mock/store";
import { seedChecklist } from "../mock/seed";
import { logActivity } from "./log";
import type { ChecklistTest, Conclusion } from "./types";

const key = (id: string) => `kien-mock-checklist-v1-${id}`;

/** N/A items sort to the bottom; otherwise catalog order is kept. */
export function sortChecklist(tests: ChecklistTest[]): ChecklistTest[] {
  const rank = (t: ChecklistTest) => (t.conclusion === "na" ? 1 : 0);
  return [...tests].sort((a, b) => rank(a) - rank(b) || a.requestId.localeCompare(b.requestId));
}

// TODO(backend): GET /auditor/engagements/{id}/checklist-tests -> ChecklistTest[] (34 rows)
export async function getChecklistTests(engagementId: string): Promise<ChecklistTest[]> {
  return delay(sortChecklist(readStore(key(engagementId), () => seedChecklist(engagementId))));
}

// TODO(backend): PATCH /auditor/engagements/{id}/checklist-tests/{requestId} {conclusion}; audit-logged server-side
export async function setConclusion(engagementId: string, requestId: string, conclusion: Conclusion | null): Promise<ChecklistTest[]> {
  const next = updateStore(key(engagementId), () => seedChecklist(engagementId), (rows) => {
    const row = rows.find((r) => r.requestId === requestId);
    if (row) { row.conclusion = conclusion; row.updatedAt = new Date().toISOString(); }
  });
  logActivity(engagementId, `Set ${requestId} to ${conclusion ?? "not tested"}.`);
  return delay(sortChecklist(next));
}
