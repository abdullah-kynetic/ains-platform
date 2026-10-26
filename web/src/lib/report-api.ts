import { apiRequest, USE_MOCKS } from "./api";
import { cloneMockEngagement } from "./mock-data";
import { getWorkspace } from "./workflow-api";

export type ReportContent = {
  sections: { title: string; html: string }[];
  item_findings: Record<string, string>;
};
export type Report = {
  id: string;
  engagementId: string;
  firmId: string;
  status: "draft" | "final";
  version: number;
  content: ReportContent;
  snapshot: {
    firmName: string;
    period: string;
    scope: string;
    requests: {
      requestId: string;
      title: string;
      status: string;
      restricted: boolean;
    }[];
  };
  finalizedAt: string | null;
  contentSha256: string | null;
  updatedAt: string;
};
const key = "kien-synthetic-reports-v1";
function stored(): Report[] {
  return JSON.parse(localStorage.getItem(key) ?? "[]");
}
function persist(report: Report) {
  localStorage.setItem(
    key,
    JSON.stringify([...stored().filter((r) => r.id !== report.id), report]),
  );
  return report;
}
export async function listReports(): Promise<Report[]> {
  return USE_MOCKS ? stored() : apiRequest("/auditor/reports");
}
export async function createReport(engagementId: string): Promise<Report> {
  if (!USE_MOCKS)
    return apiRequest("/auditor/reports", {
      method: "POST",
      body: JSON.stringify({ engagement_id: engagementId }),
    });
  const existing = stored().find((r) => r.engagementId === engagementId);
  if (existing) return existing;
  const data = cloneMockEngagement();
  const workspace = await getWorkspace(engagementId);
  return persist({
    id: crypto.randomUUID(),
    engagementId,
    firmId: "synthetic-firm",
    status: "draft",
    version: 1,
    content: {
      sections: [
        { title: "Scope", html: "<p>FINRA Rule 3310 Independent AML Test</p>" },
        { title: "Testing approach", html: "<p></p>" },
        { title: "Findings", html: "<p></p>" },
        { title: "Conclusion and follow-up", html: "<p></p>" },
      ],
      item_findings: {},
    },
    snapshot: {
      firmName: data.firmName,
      period: `${data.reviewPeriod.start} – ${data.reviewPeriod.end}`,
      scope: data.engagementType,
      requests: workspace.requests.map((r) => ({
        requestId: r.requestId,
        title: r.title,
        status: r.status ?? "requested",
        restricted: r.restricted,
      })),
    },
    finalizedAt: null,
    contentSha256: null,
    updatedAt: new Date().toISOString(),
  });
}
export async function getReport(id: string): Promise<Report> {
  if (!USE_MOCKS) return apiRequest(`/auditor/reports/${id}`);
  const report = stored().find((r) => r.id === id);
  if (!report) throw new Error("Report not found");
  return report;
}
export async function saveReport(
  report: Report,
  content: ReportContent,
): Promise<Report> {
  if (!USE_MOCKS)
    return apiRequest(`/auditor/reports/${report.id}`, {
      method: "PATCH",
      body: JSON.stringify({ version: report.version, content }),
    });
  if (report.status !== "draft") throw new Error("Final reports are locked");
  const workspace = await getWorkspace(report.engagementId);
  return persist({
    ...report,
    content,
    version: report.version + 1,
    snapshot: {
      ...report.snapshot,
      requests: workspace.requests.map((r) => ({
        requestId: r.requestId,
        title: r.title,
        status: r.status ?? "requested",
        restricted: r.restricted,
      })),
    },
  });
}
export async function transitionReport(
  report: Report,
  action: "finalize" | "reopen",
): Promise<Report> {
  if (!USE_MOCKS)
    return apiRequest(`/auditor/reports/${report.id}/${action}`, {
      method: "POST",
      body: JSON.stringify({
        version: report.version,
        ...(action === "finalize" ? { attestation: true } : {}),
      }),
    });
  return persist({
    ...report,
    status: action === "finalize" ? "final" : "draft",
    version: report.version + 1,
    finalizedAt: action === "finalize" ? new Date().toISOString() : null,
  });
}
