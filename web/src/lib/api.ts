import type { Engagement } from "./checklist";
import { cloneMockEngagement, saveMockEngagement, invalidateMockDecision } from "./mock-data";
import catalog from "../../.generated/catalog.json";

export const USE_MOCKS = process.env.NEXT_PUBLIC_USE_MOCKS === "true";
export const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(
  /\/$/,
  "",
);

const configuredMaxMb = Number(process.env.NEXT_PUBLIC_MAX_UPLOAD_MB ?? "100");
export const MAX_UPLOAD_BYTES =
  (Number.isFinite(configuredMaxMb) && configuredMaxMb > 0 ? configuredMaxMb : 100) *
  1024 *
  1024;

async function responseError(response: Response): Promise<Error> {
  let detail = `Request failed (${response.status})`;
  try {
    const body = (await response.json()) as { detail?: string };
    if (body.detail) detail = body.detail;
  } catch {
    // The status-only message is safe and useful when the response is not JSON.
  }
  return new Error(detail);
}

export async function apiRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    credentials: "include",
    headers: {
      ...(init.body ? { "Content-Type": "application/json" } : {}),
      ...init.headers,
    },
    cache: "no-store",
  });
  if (!response.ok) throw await responseError(response);
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export type UserRole = "client" | "auditor";

export type SessionUser = {
  id: string;
  email: string;
  name: string;
  role: UserRole;
  firm_id: string | null;
};

export type SessionData = { user: SessionUser };

const mockSession: SessionData = {
  user: {
    id: "synthetic-client",
    email: "client@example.invalid",
    name: "Synthetic Client",
    role: "client",
    firm_id: "synthetic-firm",
  },
};

export async function getSession(): Promise<SessionData> {
  if (USE_MOCKS) return { user: { ...mockSession.user, role: localStorage.getItem("ains-synthetic-role") === "auditor" ? "auditor" : "client" } };
  return apiRequest<SessionData>("/auth/session");
}

export async function passwordSignIn(
  email: string,
  password: string,
  mfaCode?: string,
): Promise<SessionData> {
  return apiRequest<SessionData>("/auth/password", {
    method: "POST",
    body: JSON.stringify({ email, password, mfa_code: mfaCode || null }),
  });
}

export async function requestMagicLink(email: string): Promise<void> {
  await apiRequest<{ status: string }>("/auth/magic-link", {
    method: "POST",
    body: JSON.stringify({ email }),
  });
}

export async function verifyMagicLink(token: string, mfaCode?: string): Promise<SessionData> {
  return apiRequest<SessionData>("/auth/magic-link/verify", {
    method: "POST",
    body: JSON.stringify({ token, mfa_code: mfaCode || null }),
  });
}

export async function signOut(): Promise<void> {
  if (!USE_MOCKS) await apiRequest<void>("/auth/sign-out", { method: "POST" });
}

export type NAReviewState = "pending" | "approved" | "rejected" | null;
export type Question = {
  itemId: string;
  sectionTitle: string;
  question: string;
  answer: boolean | null;
  naReviewState: NAReviewState;
  whenNo: string;
  representation: string | null;
};
export type Questionnaire = { engagementId: string; questions: Question[] };

const mockQuestions: Question[] = catalog.requests.filter((request) => request.conditions).map((request) => ({
  itemId: request.id,
  sectionTitle: catalog.sections.find((section) => section.id === request.section)!.title,
  question: request.conditions!.question,
  answer: null,
  naReviewState: null,
  whenNo: request.conditions!.when_no,
  representation: null,
}));

export async function getQuestionnaire(engagementId: string): Promise<Questionnaire> {
  if (USE_MOCKS) {
    const saved = localStorage.getItem("ains-synthetic-questionnaire-v1");
    return { engagementId, questions: saved ? JSON.parse(saved) : structuredClone(mockQuestions) };
  }
  return apiRequest<Questionnaire>(
    `/engagements/${encodeURIComponent(engagementId)}/questionnaire`,
  );
}

export async function saveQuestionnaire(
  engagementId: string,
  answers: Array<{ itemId: string; applies: boolean; representation?: string }>,
): Promise<Questionnaire> {
  if (USE_MOCKS) {
    const current = await getQuestionnaire(engagementId);
    const data = cloneMockEngagement();
    for (const answer of answers) {
      const question = current.questions.find((question) => question.itemId === answer.itemId);
      if (!question) throw new Error("Question not found.");
      if (!answer.applies && question.whenNo === "representation_required" && !answer.representation) throw new Error("Confirm the no-activity representation.");
      if (question.answer === answer.applies && question.representation === (answer.applies ? null : answer.representation ?? null)) continue;
      invalidateMockDecision(answer.itemId, true);
      question.answer = answer.applies;
      question.naReviewState = answer.applies ? null : "pending";
      question.representation = answer.applies ? null : answer.representation ?? null;
      const item = data.sections.flatMap((section) => section.items).find((item) => item.id === answer.itemId);
      if (item) { item.canUpload = answer.applies; item.naReviewState = question.naReviewState; item.representation = question.representation; item.status = answer.applies ? "requested" : "with_auditor"; }
    }
    localStorage.setItem("ains-synthetic-questionnaire-v1", JSON.stringify(current.questions));
    saveMockEngagement(data);
    return current;
  }
  return apiRequest<Questionnaire>(
    `/engagements/${encodeURIComponent(engagementId)}/questionnaire/answers`,
    { method: "POST", body: JSON.stringify({ answers }) },
  );
}

export type Citation = { document?: string; page: number; quote?: string | null };
export type AuditorCheck = {
  id: string;
  checkType: string;
  status: string;
  details: Record<string, unknown>;
  citations: Citation[];
  durationMs: number | null;
};
export type AuditorEvidence = {
  id: string;
  name: string;
  egnytePath: string;
  sha256: string;
  version: string;
  checks: AuditorCheck[];
};
export type AuditorFinding = {
  id: string;
  title: string;
  body: string;
  severity: "low" | "moderate" | "high" | "critical";
  citations: Citation[];
  reviewState: "pending" | "accepted" | "edited" | "rejected";
};
export type AuditorQueueItem = {
  firmName: string;
  engagementId: string;
  itemId: string;
  itemTitle: string;
  clientStatus: string;
  naReviewState: NAReviewState;
  evidence: AuditorEvidence[];
  findings: AuditorFinding[];
};

export async function getAuditorQueue(): Promise<AuditorQueueItem[]> {
  return apiRequest<AuditorQueueItem[]>("/auditor/queue");
}

export async function reviewFinding(
  findingId: string,
  decision: {
    action: "accept" | "edit" | "reject";
    title?: string;
    body?: string;
    severity?: AuditorFinding["severity"];
    citations?: Citation[];
  },
): Promise<AuditorFinding> {
  return apiRequest<AuditorFinding>(`/auditor/findings/${encodeURIComponent(findingId)}`, {
    method: "PATCH",
    body: JSON.stringify(decision),
  });
}

export async function reviewNotApplicable(
  engagementId: string,
  itemId: string,
  decision: "approve" | "reject",
): Promise<Question> {
  return apiRequest<Question>(
    `/engagements/${encodeURIComponent(engagementId)}/questionnaire/items/${encodeURIComponent(itemId)}/na-review`,
    { method: "POST", body: JSON.stringify({ decision }) },
  );
}

export async function downloadDraftReport(
  engagementId: string,
  format: "docx" | "pdf",
): Promise<void> {
  const response = await fetch(
    `${API_URL}/auditor/engagements/${encodeURIComponent(engagementId)}/report?format=${format}`,
    { method: "POST", credentials: "include" },
  );
  if (!response.ok) throw await responseError(response);
  const blob = await response.blob();
  const disposition = response.headers.get("Content-Disposition") ?? "";
  const match = disposition.match(/filename="([^"]+)"/);
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = match?.[1] ?? `ains-draft-report.${format}`;
  link.click();
  URL.revokeObjectURL(link.href);
}

export async function getEngagement(): Promise<Engagement> {
  if (USE_MOCKS) {
    await new Promise((resolve) => setTimeout(resolve, 150));
    const data = cloneMockEngagement();
    data.sections = data.sections.map((section) => ({ ...section, items: section.items.filter((item) => item.naReviewState !== "approved") }));
    return data;
  }
  const response = await fetch(`${API_URL}/engagements/current`, {
    credentials: "include",
    cache: "no-store",
  });
  if (!response.ok) throw await responseError(response);
  return (await response.json()) as Engagement;
}

export async function uploadDocument(
  engagementId: string,
  itemId: string,
  file: File,
  onProgress: (pct: number) => void,
): Promise<UploadReceipt> {
  if (file.size > MAX_UPLOAD_BYTES) {
    throw new Error(`File is larger than ${Math.round(MAX_UPLOAD_BYTES / 1024 / 1024)} MB.`);
  }
  if (USE_MOCKS) {
    const data = cloneMockEngagement();
    const item = data.sections.flatMap((section) => section.items).find((item) => item.id === itemId);
    if (!item || item.restricted || item.canUpload === false) throw new Error("This request cannot accept portal uploads.");
    const suffix = `.${file.name.split(".").pop()?.toLowerCase()}`;
    if (!item.allowedEvidenceTypes.includes(suffix)) throw new Error("Wrong file type for this request.");
    if (!file.size) throw new Error("File is empty.");
    const sha256 = Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256", await file.arrayBuffer())))
      .map((byte) => byte.toString(16).padStart(2, "0")).join("");
    const receipt = { id: crypto.randomUUID(), name: file.name, size: file.size, sha256, version: "synthetic-1", status: "checking" as const };
    item.files.push({ ...receipt, uploadedAt: new Date().toISOString() });
    item.status = "checking";
    invalidateMockDecision(itemId);
    saveMockEngagement(data);
    onProgress(100);
    return receipt;
  }

  return await new Promise<UploadReceipt>((resolve, reject) => {
    const request = new XMLHttpRequest();
    request.open(
      "POST",
      `${API_URL}/engagements/${encodeURIComponent(engagementId)}/items/${encodeURIComponent(itemId)}/documents`,
    );
    request.withCredentials = true;
    request.timeout = 120000;
    request.ontimeout = () => reject(new Error("Upload timed out. Check the checklist before retrying."));
    request.upload.onprogress = (event) => {
      if (event.lengthComputable) onProgress((event.loaded / event.total) * 100);
    };
    request.onerror = () => reject(new Error("Upload failed because the API could not be reached."));
    request.onload = () => {
      if (request.status >= 200 && request.status < 300) {
        onProgress(100);
        try { resolve(JSON.parse(request.responseText) as UploadReceipt); }
        catch { reject(new Error("The server did not return a valid receipt. Refresh before retrying.")); }
        return;
      }
      let message = `Upload failed (${request.status}).`;
      try {
        const body = JSON.parse(request.responseText) as { detail?: string };
        if (body.detail) message = body.detail;
      } catch {
        // Keep the status-only message for non-JSON responses.
      }
      reject(new Error(message));
    };
    const form = new FormData();
    form.append("file", file);
    request.send(form);
  });
}

export type UploadReceipt = { id: string; name: string; size: number; sha256: string; version: string; status: string };
