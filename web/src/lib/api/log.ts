import { delay, readStore, writeStore, uid } from "../mock/store";
import { CURRENT_USER, seedActivity } from "../mock/seed";
import type { ActivityEntry } from "./types";

const key = (id: string) => `kien-mock-activity-${id}`;

/** Appends to the engagement activity log. TODO(backend): the server writes the audit trail; this is display-only. */
export function logActivity(engagementId: string, action: string, actor = CURRENT_USER) {
  const list = readStore<ActivityEntry[]>(key(engagementId), () => seedActivity(engagementId));
  writeStore(key(engagementId), [{ id: uid("act"), engagementId, at: new Date().toISOString(), actor, action }, ...list]);
}

// TODO(backend): GET /auditor/engagements/{id}/activity -> ActivityEntry[]
export async function listActivity(engagementId: string): Promise<ActivityEntry[]> {
  return delay(readStore<ActivityEntry[]>(key(engagementId), () => seedActivity(engagementId)));
}
