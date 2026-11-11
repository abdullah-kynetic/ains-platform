import { apiRequest, USE_MOCKS } from "../api";
import { delay, readStore, updateStore } from "../mock/store";
import { getChecklistTests } from "./checklist";
import { listFindings } from "./findings";
import { listSamples, sampleStats } from "./samples";
import { getEngagementSummary } from "./clients";
import { logActivity } from "./log";
import type { ReportDraft, ReportSection } from "./types";

const key = (id: string) => `kien-mock-report-edits-v1-${id}`;
const escapeHtml = (s: string) => s.replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]!);

/** Sections assembled from approved findings plus tested results. Drafts are never included. */
// TODO(backend): GET /auditor/engagements/{id}/report-draft -> ReportDraft (server assembles from stored findings)
export async function buildReport(engagementId: string): Promise<ReportDraft> {
  if (!USE_MOCKS) return apiRequest(`/auditor/engagements/${encodeURIComponent(engagementId)}/report-draft`);
  const [summary, tests, findings, samples] = await Promise.all([getEngagementSummary(engagementId), getChecklistTests(engagementId), listFindings(engagementId), listSamples(engagementId)]);
  const edits = readStore<Record<string, string>>(key(engagementId), () => ({}));
  const count = (c: string) => tests.filter((t) => t.conclusion === c).length;
  const included = findings.filter((f) => f.status !== "draft");
  const exceptions = samples.reduce((n, s) => n + sampleStats(s).exceptions, 0);
  const auto: ReportSection[] = [
    { id: "scope", title: "Scope and objective", body: `Kien Solutions performed an independent test of ${summary?.firmName ?? "the firm"}’s anti-money-laundering program for ${summary?.period ?? "the review period"}, as required by FINRA Rule 3310(c).` },
    { id: "approach", title: "Approach", body: `We tested ${tests.length - count("na")} of ${tests.length} requests (${count("na")} marked does not apply). Sample testing covered ${samples.length} populations with ${exceptions} exception${exceptions === 1 ? "" : "s"} noted.` },
    { id: "results", title: "Summary of results", body: `Pass: ${count("pass")}. Partial: ${count("partial")}. Fail: ${count("fail")}. Does not apply: ${count("na")}. Not yet concluded: ${tests.filter((t) => t.conclusion === null).length}.` },
    ...included.map((f, i): ReportSection => ({ id: `finding-${f.id}`, title: `Finding ${i + 1}: ${f.title}`, body: `Rule: ${f.rule}\nCondition: ${f.condition}\nCause: ${f.cause}\nEffect: ${f.effect}\nRecommendation: ${f.recommendation}\nSeverity: ${f.severity}\nManagement response: ${f.managementResponse || "Not yet received."}` })),
    { id: "limitations", title: "Limitations", body: "This report is based on documents provided by the firm. It is not a guarantee that no violations exist. It is draft until signed by the credentialed auditor." },
  ];
  return delay({ engagementId, generatedAt: new Date().toISOString(), sections: auto.map((s) => ({ ...s, body: edits[s.id] ?? s.body })) });
}

// TODO(backend): PUT /auditor/engagements/{id}/report-draft/sections/{sectionId}
export async function saveReportSection(engagementId: string, sectionId: string, body: string): Promise<void> {
  if (!USE_MOCKS) {
    await apiRequest(`/auditor/engagements/${encodeURIComponent(engagementId)}/report-draft/sections/${encodeURIComponent(sectionId)}`, { method: "PUT", body: JSON.stringify({ body }) });
    return;
  }
  updateStore(key(engagementId), () => ({} as Record<string, string>), (e) => { e[sectionId] = body; });
  logActivity(engagementId, `Edited report section “${sectionId}”.`);
  return delay(undefined, 0);
}

/** SHA-256 over the section text, so any edit after sign-off is visible as a different fingerprint. */
export async function reportFingerprint(sections: ReportSection[]): Promise<string> {
  const data = new TextEncoder().encode(sections.map((s) => `${s.title}\n${s.body}`).join("\n\n"));
  const digest = await crypto.subtle.digest("SHA-256", data);
  return Array.from(new Uint8Array(digest)).map((b) => b.toString(16).padStart(2, "0")).join("");
}

export function reportHtml(title: string, sections: ReportSection[], fingerprint?: string | null) {
  const body = sections.map((s) => `<h2>${escapeHtml(s.title)}</h2>${s.body.split("\n").map((l) => `<p>${escapeHtml(l)}</p>`).join("")}`).join("");
  return `<html><head><meta charset="utf-8"><title>${escapeHtml(title)}</title></head><body><h1>${escapeHtml(title)}</h1>${body}${fingerprint ? `<p><small>Report fingerprint (SHA-256): ${fingerprint}</small></p>` : ""}</body></html>`;
}

/** Word export. TODO(backend): GET /auditor/engagements/{id}/report.docx (server-rendered from templates/report). */
export function downloadWord(title: string, sections: ReportSection[], fingerprint?: string | null) {
  const blob = new Blob([reportHtml(title, sections, fingerprint)], { type: "application/msword" });
  const url = URL.createObjectURL(blob);
  const a = Object.assign(document.createElement("a"), { href: url, download: `${title.replace(/[^a-z0-9]+/gi, "-").toLowerCase()}.doc` });
  a.click();
  URL.revokeObjectURL(url);
}
