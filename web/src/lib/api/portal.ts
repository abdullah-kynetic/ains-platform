import { delay, readStore, updateStore } from "../mock/store";
import { seedFindings } from "../mock/seed";
import type { ClientPortalFinding, ClientPortalInvoice, ClientPortalReport, Finding } from "./types";
import { logActivity } from "./log";

const findingsKey = "kien-mock-findings-v1";
/** Clients only ever see findings the auditor has formally issued. Drafts and approved-but-unissued findings never leave the auditor side. */
const visible = (f: Finding) => f.status === "issued" || f.status === "responded" || f.status === "closed";

// TODO(backend): GET /client/findings -> ClientPortalFinding[] (server filters to issued findings for the caller's firm)
export async function listPortalFindings(): Promise<ClientPortalFinding[]> {
  return delay(readStore<Finding[]>(findingsKey, seedFindings).filter((f) => f.engagementId === "eng-synthetic-001" && visible(f)).map(({ id, title, rule, condition, recommendation, severity, managementResponse, respondedAt, status }) => ({ id, title, rule, condition, recommendation, severity, managementResponse, respondedAt, status })));
}

// TODO(backend): POST /client/findings/{id}/response {text}; only allowed while status is "issued"
export async function respondToFinding(id: string, text: string): Promise<ClientPortalFinding[]> {
  if (!text.trim()) throw new Error("Write a response before submitting.");
  let engagementId = "eng-synthetic-001";
  updateStore<Finding[]>(findingsKey, seedFindings, (rows) => {
    const f = rows.find((r) => r.id === id);
    if (!f || f.status !== "issued") throw new Error("This finding is not open for a response.");
    f.managementResponse = text.trim(); f.respondedAt = new Date().toISOString(); f.status = "responded"; engagementId = f.engagementId;
  });
  logActivity(engagementId, "Client submitted a management response.", "Maya Okafor (client)");
  return listPortalFindings();
}

// TODO(backend): GET /client/reports -> ClientPortalReport[]; only signed reports are `available`
export async function listPortalReports(): Promise<ClientPortalReport[]> {
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

// TODO(backend): GET /client/invoices -> ClientPortalInvoice[] (issuing firm's invoices for this client only)
export async function listPortalInvoices(): Promise<ClientPortalInvoice[]> {
  return delay([
    { id: "inv-1", number: "KIEN-0007", issued: "2026-10-01", due: "2026-10-31", amountCents: 1_250_000, status: "overdue" },
    { id: "inv-2", number: "KIEN-0004", issued: "2025-11-30", due: "2025-12-30", amountCents: 1_100_000, status: "paid" },
  ]);
}
