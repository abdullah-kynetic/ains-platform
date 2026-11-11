import { apiRequest, USE_MOCKS } from "../api";
import { delay, readStore, updateStore, uid } from "../mock/store";
import { seedSamples } from "../mock/seed";
import { logActivity } from "./log";
import type { SampleResult, SampleSet } from "./types";

const key = "kien-mock-samples-v1";
const all = () => readStore<SampleSet[]>(key, seedSamples);

// TODO(backend): GET /auditor/engagements/{id}/samples -> SampleSet[]
export async function listSamples(engagementId: string): Promise<SampleSet[]> {
  if (!USE_MOCKS) return apiRequest(`/auditor/engagements/${encodeURIComponent(engagementId)}/samples`);
  return delay(all().filter((s) => s.engagementId === engagementId));
}

// TODO(backend): POST /auditor/engagements/{id}/samples; server selects items from the population file when given a seed
export async function createSample(engagementId: string, input: Pick<SampleSet, "area" | "requestId" | "population" | "sampleSize" | "method">): Promise<SampleSet> {
  const set: SampleSet = {
    ...input, id: uid("smp"), engagementId,
    items: Array.from({ length: input.sampleSize }, (_, i) => ({ id: uid("itm"), reference: `ITEM-${String(i + 1).padStart(3, "0")}`, result: "pending", note: "" })),
  };
  updateStore(key, seedSamples, (rows) => [...rows, set]);
  logActivity(engagementId, `Created sample “${input.area}” (${input.sampleSize} of ${input.population}).`);
  return delay(set);
}

// TODO(backend): PATCH /auditor/samples/{setId}/items/{itemId} {result, note}
export async function setSampleResult(setId: string, itemId: string, result: SampleResult, note?: string): Promise<SampleSet[]> {
  let engagementId = "";
  const next = updateStore(key, seedSamples, (rows) => {
    const set = rows.find((s) => s.id === setId);
    const item = set?.items.find((i) => i.id === itemId);
    if (set && item) { engagementId = set.engagementId; item.result = result; if (note !== undefined) item.note = note; }
  });
  if (engagementId) logActivity(engagementId, `Recorded sample result “${result}”.`);
  return delay(next.filter((s) => s.engagementId === engagementId));
}

export const sampleStats = (set: SampleSet) => ({
  tested: set.items.filter((i) => i.result !== "pending").length,
  exceptions: set.items.filter((i) => i.result === "exception").length,
});
