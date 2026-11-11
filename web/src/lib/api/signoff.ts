import { apiRequest, USE_MOCKS } from "../api";
import { delay, readStore, updateStore } from "../mock/store";
import { seedIndependence, seedSignoff, PARTNER, REVIEWER, CURRENT_USER } from "../mock/seed";
import { getChecklistTests } from "./checklist";
import { findingBlockers, listFindings } from "./findings";
import { listSamples } from "./samples";
import { listWorkpapers } from "./workpapers";
import { buildReport, reportFingerprint } from "./report";
import { logActivity } from "./log";
import type { IndependenceRecord, SignoffState } from "./types";

const soKey = (id: string) => `kien-mock-signoff-v1-${id}`;
const indKey = (id: string) => `kien-mock-independence-v1-${id}`;

// TODO(backend): GET /auditor/engagements/{id}/independence -> IndependenceRecord
export async function getIndependence(engagementId: string): Promise<IndependenceRecord> {
  if (!USE_MOCKS) return apiRequest(`/auditor/engagements/${encodeURIComponent(engagementId)}/independence`);
  return delay(readStore(indKey(engagementId), () => seedIndependence(engagementId)));
}

// TODO(backend): PUT /auditor/engagements/{id}/independence; declaration is attributed to the signed-in auditor
export async function saveIndependence(engagementId: string, input: Pick<IndependenceRecord, "answers" | "conflicts" | "safeguards">): Promise<IndependenceRecord> {
  if (!USE_MOCKS) return apiRequest(`/auditor/engagements/${encodeURIComponent(engagementId)}/independence`, { method: "PUT", body: JSON.stringify(input) });
  const anyYes = input.answers.some((a) => a.answer === "yes");
  const complete = input.answers.every((a) => a.answer !== null);
  const record: IndependenceRecord = {
    engagementId, ...input,
    conclusion: !complete ? null : !anyYes ? "independent" : input.safeguards.trim() ? "safeguards_required" : "not_independent",
    declaredBy: complete ? CURRENT_USER : null, declaredAt: complete ? new Date().toISOString() : null,
  };
  updateStore(indKey(engagementId), () => seedIndependence(engagementId), () => record);
  logActivity(engagementId, `Recorded independence check: ${record.conclusion ?? "incomplete"}.`);
  return delay(record);
}

// TODO(backend): GET /auditor/engagements/{id}/signoff -> SignoffState
export async function getSignoff(engagementId: string): Promise<SignoffState> {
  if (!USE_MOCKS) return apiRequest(`/auditor/engagements/${encodeURIComponent(engagementId)}/signoff`);
  return delay(readStore(soKey(engagementId), () => seedSignoff(engagementId)));
}

/** Everything that must be true before a second reviewer can approve. */
export async function signoffBlockers(engagementId: string): Promise<string[]> {
  if (!USE_MOCKS) return apiRequest(`/auditor/engagements/${encodeURIComponent(engagementId)}/signoff/blockers`);
  const [tests, findings, samples, workpapers, independence] = await Promise.all([getChecklistTests(engagementId), listFindings(engagementId), listSamples(engagementId), listWorkpapers(engagementId), getIndependence(engagementId)]);
  const out: string[] = [];
  const open = tests.filter((t) => t.conclusion === null).length;
  if (open) out.push(`${open} checklist item${open === 1 ? " has" : "s have"} no conclusion.`);
  const pending = samples.reduce((n, s) => n + s.items.filter((i) => i.result === "pending").length, 0);
  if (pending) out.push(`${pending} sample item${pending === 1 ? " is" : "s are"} untested.`);
  const unreviewed = workpapers.filter((w) => !w.reviewedAt).length;
  if (unreviewed) out.push(`${unreviewed} workpaper${unreviewed === 1 ? " needs" : "s need"} review.`);
  const drafts = findings.filter((f) => f.status === "draft" || findingBlockers(f).length);
  if (drafts.length) out.push(`${drafts.length} finding${drafts.length === 1 ? " is" : "s are"} still a draft.`);
  if (!independence.conclusion || independence.conclusion === "not_independent") out.push("Independence has not been cleared.");
  return out;
}

// TODO(backend): POST /auditor/engagements/{id}/signoff/review. Server rejects the preparer and requires the reviewer role.
export async function approveAsReviewer(engagementId: string, note: string): Promise<SignoffState> {
  if (!USE_MOCKS) return apiRequest(`/auditor/engagements/${encodeURIComponent(engagementId)}/signoff/review`, { method: "POST", body: JSON.stringify({ note }) });
  if ((await signoffBlockers(engagementId)).length) throw new Error("Resolve the blockers before approving.");
  const next = updateStore(soKey(engagementId), () => seedSignoff(engagementId), (s) => { s.reviewer = { name: REVIEWER, approvedAt: new Date().toISOString(), note }; });
  logActivity(engagementId, "Second reviewer approved the file.", REVIEWER);
  return delay(next);
}

// TODO(backend): POST /auditor/engagements/{id}/signoff/partner {typedName}. The server computes the fingerprint and records the signature.
export async function partnerSign(engagementId: string, typedName: string): Promise<SignoffState> {
  if (!USE_MOCKS) return apiRequest(`/auditor/engagements/${encodeURIComponent(engagementId)}/signoff/partner`, { method: "POST", body: JSON.stringify({ typedName }) });
  const current = await getSignoff(engagementId);
  if (!current.reviewer.approvedAt) throw new Error("The second reviewer must approve first.");
  if (typedName.trim().toLowerCase() !== PARTNER.toLowerCase()) throw new Error(`Type “${PARTNER}” exactly to sign.`);
  const fingerprint = await reportFingerprint((await buildReport(engagementId)).sections);
  const next = updateStore(soKey(engagementId), () => seedSignoff(engagementId), (s) => { s.partner = { name: PARTNER, signedAt: new Date().toISOString(), fingerprint }; });
  logActivity(engagementId, "Partner signed the report.", PARTNER);
  return delay(next);
}

// TODO(backend): POST /auditor/engagements/{id}/complete (requires a partner signature)
export async function completeEngagement(engagementId: string): Promise<SignoffState> {
  if (!USE_MOCKS) {
    await apiRequest(`/auditor/engagements/${encodeURIComponent(engagementId)}/complete`, { method: "POST", body: "{}" });
    return getSignoff(engagementId);
  }
  const current = await getSignoff(engagementId);
  if (!current.partner.signedAt) throw new Error("A partner signature is required to complete the engagement.");
  const next = updateStore(soKey(engagementId), () => seedSignoff(engagementId), (s) => { s.completedAt = new Date().toISOString(); });
  logActivity(engagementId, "Marked the engagement complete.");
  return delay(next);
}
