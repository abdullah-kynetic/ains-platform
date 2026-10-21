import type { Engagement } from "./checklist";

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

async function apiRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
  if (USE_MOCKS) return (await import("./demo")).demoRequest<T>(path, init);
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
  if (USE_MOCKS) {
    const requested = new URLSearchParams(window.location.search).get("demo");
    if (requested === "client" || requested === "auditor") sessionStorage.setItem("ains-demo-role", requested);
    const role = sessionStorage.getItem("ains-demo-role") === "auditor" ? "auditor" : "client";
    return { user: { ...mockSession.user, role, name: role === "auditor" ? "Synthetic Auditor" : "Synthetic Client" } };
  }
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
  negativeAnswerInstruction?: string | null;
};
export type Questionnaire = { engagementId: string; questions: Question[] };

export async function getQuestionnaire(engagementId: string): Promise<Questionnaire> {
  if (USE_MOCKS) return (await import("./demo")).demoQuestionnaire(engagementId);
  return apiRequest<Questionnaire>(
    `/engagements/${encodeURIComponent(engagementId)}/questionnaire`,
  );
}

export async function saveQuestionnaire(
  engagementId: string,
  answers: Array<{ itemId: string; applies: boolean }>,
): Promise<Questionnaire> {
  if (USE_MOCKS) {
    return (await import("./demo")).demoAnswers(engagementId, answers);
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
  representationReviewed = false,
): Promise<Question> {
  return apiRequest<Question>(
    `/engagements/${encodeURIComponent(engagementId)}/questionnaire/items/${encodeURIComponent(itemId)}/na-review`,
    { method: "POST", body: JSON.stringify({ decision, representationReviewed }) },
  );
}

export type ManagedEngagement = {
  id: string;
  firmId: string;
  firmName: string;
  status: string;
  checklistVersion: string | null;
  itemCount: number;
};

export type ChecklistReview = {
  engagement: ManagedEngagement;
  catalog: { items: Array<{
    id: string; title: string; description: string; restricted: boolean;
    review_period_rule: string; condition_question: string | null;
    negative_answer_instruction: string | null;
  }> };
  followUps: Array<{ id: string; title: string; released: boolean }>;
};

export function listManagedEngagements(): Promise<ManagedEngagement[]> {
  return apiRequest<ManagedEngagement[]>("/auditor/engagements");
}

export function createDraftEngagement(payload: {
  firmName: string; firmSlug: string; reviewPeriodStart: string;
  reviewPeriodEnd: string; dueDate: string | null;
}): Promise<ManagedEngagement> {
  return apiRequest<ManagedEngagement>("/auditor/engagements", {
    method: "POST", body: JSON.stringify(payload),
  });
}

export function getChecklistReview(id: string): Promise<ChecklistReview> {
  return apiRequest<ChecklistReview>(`/auditor/engagements/${encodeURIComponent(id)}/checklist`);
}

export function publishChecklist(id: string, reviewNotes: string): Promise<ManagedEngagement> {
  return apiRequest<ManagedEngagement>(`/auditor/engagements/${encodeURIComponent(id)}/publish`, {
    method: "POST", body: JSON.stringify({ confirmChecklistReviewed: true, reviewNotes }),
  });
}

export function releaseFollowUp(id: string, itemId: string, selectionNotes: string): Promise<void> {
  return apiRequest<void>(`/auditor/engagements/${encodeURIComponent(id)}/items/${encodeURIComponent(itemId)}/release`, {
    method: "POST", body: JSON.stringify({ selectionNotes }),
  });
}

export async function downloadDraftReport(
  engagementId: string,
  format: "docx" | "pdf",
): Promise<void> {
  if (USE_MOCKS) throw new Error("Report downloads require the authenticated backend. Demo finding decisions are simulated.");
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
    return (await import("./demo")).demoEngagement();
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
): Promise<void> {
  if (file.size > MAX_UPLOAD_BYTES) {
    throw new Error(`File is larger than ${Math.round(MAX_UPLOAD_BYTES / 1024 / 1024)} MB.`);
  }
  if (USE_MOCKS) {
    (await import("./demo")).demoUpload(itemId, file);
    for (const pct of [20, 45, 70, 100]) {
      await new Promise((resolve) => setTimeout(resolve, 120));
      onProgress(pct);
    }
    return;
  }

  await new Promise<void>((resolve, reject) => {
    const request = new XMLHttpRequest();
    request.open(
      "POST",
      `${API_URL}/engagements/${encodeURIComponent(engagementId)}/items/${encodeURIComponent(itemId)}/documents`,
    );
    request.withCredentials = true;
    request.upload.onprogress = (event) => {
      if (event.lengthComputable) onProgress((event.loaded / event.total) * 100);
    };
    request.onerror = () => reject(new Error("Upload failed because the API could not be reached."));
    request.onload = () => {
      if (request.status >= 200 && request.status < 300) {
        onProgress(100);
        resolve();
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
