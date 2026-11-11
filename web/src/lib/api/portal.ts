import { apiRequest, getEngagement, USE_MOCKS } from "../api";
import { delay, readStore, updateStore } from "../mock/store";
import { seedFindings } from "../mock/seed";
import type { ClientPortalInvoice, ClientPortalReport, Finding, ResponseRequest } from "./types";
import { logActivity } from "./log";

const findingsKey = "kien-mock-findings-v1";
const requestsKey = "kien-mock-response-requests-v1";
export type StoredRequest = ResponseRequest & { engagementId: string; findingId: string };
export const seedResponseRequests = (): StoredRequest[] => [
  { id: "rr-1", engagementId: "eng-synthetic-001", findingId: "fnd-1", title: "Alert-closure documentation", requestText: "Please describe how your team documents the reason for closing a transaction-monitoring alert, and confirm what changes you plan to make.", status: "open", response: "", respondedAt: null, releasedAt: "2026-10-29T12:00:00.000Z" },
  { id: "rr-2", engagementId: "eng-synthetic-001", findingId: "fnd-2", title: "Risk assessment refresh", requestText: "Please confirm when your AML risk assessment was last refreshed and when the next refresh is planned.", status: "responded", response: "We agree. The assessment will be refreshed by 12/31 and added to the compliance calendar.", respondedAt: "2026-10-30T09:40:00.000Z", releasedAt: "2026-10-29T12:00:00.000Z" },
];
const strip = (r: StoredRequest): ResponseRequest => ({ id: r.id, title: r.title, requestText: r.requestText, status: r.status, response: r.response, respondedAt: r.respondedAt, releasedAt: r.releasedAt });

/** The signed-in client's engagement (client routes are scoped under /engagements/{id}). */
export async function clientEngagementId(): Promise<string> {
  return (await getEngagement()).id;
}

/** Auditor action: release one item to the client with text the auditor wrote. POST /auditor/findings/{id}/response-request {title, requestText}; only for approved findings. */
export async function releaseResponseRequest(findingId: string, title: string, requestText: string): Promise<void> {
  if (!title.trim() || !requestText.trim()) throw new Error("Write a title and the request for the client.");
  if (!USE_MOCKS) {
    await apiRequest(`/auditor/findings/${encodeURIComponent(findingId)}/response-request`, { method: "POST", body: JSON.stringify({ title: title.trim(), requestText: requestText.trim() }) });
    return;
  }
  let engagementId = "";
  updateStore<Finding[]>(findingsKey, seedFindings, (rows) => {
    const f = rows.find((r) => r.id === findingId);
    if (!f || f.status !== "approved") throw new Error("Approve the finding before requesting a response.");
    f.status = "issued"; f.updatedAt = new Date().toISOString(); engagementId = f.engagementId;
  });
  updateStore<StoredRequest[]>(requestsKey, seedResponseRequests, (rows) => [...rows, { id: `rr-${Date.now()}`, engagementId, findingId, title: title.trim(), requestText: requestText.trim(), status: "open", response: "", respondedAt: null, releasedAt: new Date().toISOString() }]);
  logActivity(engagementId, `Requested a management response: “${title.trim()}”.`);
  return delay(undefined, 0);
}

// GET /engagements/{id}/response-requests -> ResponseRequest[] (only items an auditor explicitly released for the caller's firm)
export async function listResponseRequests(): Promise<ResponseRequest[]> {
  if (!USE_MOCKS) return apiRequest(`/engagements/${encodeURIComponent(await clientEngagementId())}/response-requests`);
  return delay(readStore<StoredRequest[]>(requestsKey, seedResponseRequests).filter((r) => r.engagementId === "eng-synthetic-001").map(strip));
}

// POST /engagements/{id}/response-requests/{rid}/response {text}; only while status is "open"
export async function respondToRequest(id: string, text: string): Promise<ResponseRequest[]> {
  if (!text.trim()) throw new Error("Write a response before submitting.");
  if (!USE_MOCKS) {
    const eid = encodeURIComponent(await clientEngagementId());
    await apiRequest(`/engagements/${eid}/response-requests/${encodeURIComponent(id)}/response`, { method: "POST", body: JSON.stringify({ text: text.trim() }) });
    return listResponseRequests();
  }
  let engagementId = "eng-synthetic-001"; let findingId = "";
  updateStore<StoredRequest[]>(requestsKey, seedResponseRequests, (rows) => {
    const r = rows.find((x) => x.id === id);
    if (!r || r.status !== "open") throw new Error("This item is not open for a response.");
    r.response = text.trim(); r.respondedAt = new Date().toISOString(); r.status = "responded"; engagementId = r.engagementId; findingId = r.findingId;
  });
  updateStore<Finding[]>(findingsKey, seedFindings, (rows) => {
    const f = rows.find((x) => x.id === findingId);
    if (f) { f.managementResponse = text.trim(); f.respondedAt = new Date().toISOString(); f.status = "responded"; }
  });
  logActivity(engagementId, "Client submitted a management response.", "Maya Okafor (client)");
  return listResponseRequests();
}

// TODO(backend): GET /client/reports -> ClientPortalReport[]; only signed reports are `available`
export async function listPortalReports(): Promise<ClientPortalReport[]> {
  if (!USE_MOCKS) return [await apiRequest<ClientPortalReport>(`/engagements/${encodeURIComponent(await clientEngagementId())}/signed-report`)];
  return delay([
    { id: "rep-2025", period: "Jan–Dec 2025", available: false, signedOn: null, signedBy: null, fingerprint: null, sections: [] },
    {
      id: "rep-2024", period: "Jan–Dec 2024", available: true, signedOn: "2025-12-12", signedBy: "Quentin",
      fingerprint: "5b1e97c2a04d83f6e1920b7c4a5d68e3f0c19a2b7d4e8f61a3c5b09d2e7f4a81",
      sections: [
        { id: "s1", title: "Scope and objective", body: "Independent test of the AML program for January–December 2024, as required by FINRA Rule 3310(c)." },
        { id: "s2", title: "Summary of results", body: "Pass: 29. Partial: 3. Fail: 0. Does not apply: 2. Two findings were issued and closed." },
        { id: "s3", title: "Limitations", body: "Based on documents provided by the firm. Not a guarantee that no violations exist." },
      ],
    },
  ]);
}

/** Client confirms the signed report by its fingerprint. POST /engagements/{id}/signed-report/confirm; this unlocks invoicing. */
export async function confirmPortalReport(fingerprint: string): Promise<void> {
  if (!USE_MOCKS) {
    await apiRequest(`/engagements/${encodeURIComponent(await clientEngagementId())}/signed-report/confirm`, { method: "POST", body: JSON.stringify({ fingerprint }) });
    return;
  }
  return delay(undefined, 0);
}

// TODO(backend): GET /client/invoices -> ClientPortalInvoice[] (issuing firm's invoices for this client only)
export async function listPortalInvoices(): Promise<ClientPortalInvoice[]> {
  if (!USE_MOCKS) return apiRequest(`/engagements/${encodeURIComponent(await clientEngagementId())}/invoices`);
  return delay([
    { id: "inv-1", number: "KIEN-0007", issued: "2026-10-01", due: "2026-10-31", amountCents: 1_250_000, status: "overdue" },
    { id: "inv-2", number: "KIEN-0004", issued: "2025-11-30", due: "2025-12-30", amountCents: 1_100_000, status: "paid" },
  ]);
}
