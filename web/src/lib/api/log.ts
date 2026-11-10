import { USE_MOCKS } from "../api";
import { getAuditorActivity } from "../workflow-api";
import { delay, readStore, writeStore, uid } from "../mock/store";
import { CURRENT_USER, seedActivity } from "../mock/seed";
import type { ActivityEntry } from "./types";

const key = (id: string) => `kien-mock-activity-${id}`;

/** Demo-only activity; live mutations append audit records on the server. */
export function logActivity(engagementId: string, action: string, actor = CURRENT_USER) {
  if (!USE_MOCKS) return; // Real audit entries are written by server mutations only.
  const list = readStore<ActivityEntry[]>(key(engagementId), () => seedActivity(engagementId));
  writeStore(key(engagementId), [{ id: uid("act"), engagementId, at: new Date().toISOString(), actor, action }, ...list]);
}

// Existing server feed returns the latest 20 events across assigned engagements.
export async function listActivity(engagementId: string): Promise<ActivityEntry[]> {
  if (!USE_MOCKS) {
    const events = await getAuditorActivity();
    return events.filter((event) => event.engagementId === engagementId).map((event) => ({
      id: event.id, engagementId, at: event.occurredAt, actor: event.actor,
      action: `${event.action} ${event.subject}`,
    }));
  }
  return delay(readStore<ActivityEntry[]>(key(engagementId), () => seedActivity(engagementId)));
}
