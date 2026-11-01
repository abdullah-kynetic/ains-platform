import type { Engagement } from "./checklist";
import {
  cloneMockEngagement,
  saveMockEngagement,
  invalidateMockDecision,
} from "./mock-data";
import catalog from "../../.generated/catalog.json";

export const USE_MOCKS = process.env.NEXT_PUBLIC_USE_MOCKS === "true";
export const API_URL = (
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"
).replace(/\/$/, "");

/** Playwright sets this so session and branding hit a mocked API. */
export const LIVE_API_FLAG = "ains-e2e-live-api";

const WRONG_PORTAL_DETAILS = new Set([
  "Session firm does not match this portal",
  "Firm portal host is required",
]);

export class ApiError extends Error {
  readonly status: number;

  constructor(status: number, detail: string) {
    super(detail);
    this.name = "ApiError";
    this.status = status;
  }
}

export function isWrongPortalStatus(status: number, detail: string): boolean {
  return status === 403 && WRONG_PORTAL_DETAILS.has(detail);
}

type WrongPortalListener = () => void;
const wrongPortalListeners = new Set<WrongPortalListener>();

export function onWrongPortal(listener: WrongPortalListener): () => void {
  wrongPortalListeners.add(listener);
  return () => wrongPortalListeners.delete(listener);
}

function noteWrongPortal(status: number, detail: string) {
  if (!isWrongPortalStatus(status, detail)) return;
  for (const listener of wrongPortalListeners) listener();
}

/** Synthetic demo stays on unless a browser test opts into the API client. */
export function clientMocksEnabled(): boolean {
  if (!USE_MOCKS) return false;
  if (typeof window === "undefined") return true;
  try {
    return window.localStorage.getItem(LIVE_API_FLAG) !== "1";
  } catch {
    return true;
  }
}

const configuredMaxMb = Number(process.env.NEXT_PUBLIC_MAX_UPLOAD_MB ?? "100");
export const MAX_UPLOAD_BYTES =
  (Number.isFinite(configuredMaxMb) && configuredMaxMb > 0
    ? configuredMaxMb
    : 100) *
  1024 *
  1024;

async function responseError(response: Response): Promise<ApiError> {
  let detail = `Request failed (${response.status})`;
  try {
    const body = (await response.json()) as { detail?: string };
    if (typeof body.detail === "string" && body.detail) detail = body.detail;
  } catch {
    // The status-only message is safe and useful when the response is not JSON.
  }
  noteWrongPortal(response.status, detail);
  return new ApiError(response.status, detail);
}

export async function apiRequest<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
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

export type AuditorMFAEnrollment = {
  secret: string;
  provisioning_uri: string;
  expires_at: string;
};

export type AuditorMFAEnrollmentComplete = SessionData & {
  recovery_codes: string[];
};

export type ClientInvitationStatus =
  | "pending"
  | "expired"
  | "revoked"
  | "accepted";

export type ClientInvitation = {
  id: string;
  firmId: string;
  engagementId: string;
  firmName: string;
  email: string;
  name: string;
  status: ClientInvitationStatus;
  expiresAt: string;
  acceptedAt: string | null;
  previewPath: string | null;
};

export type InvitationDetails = {
  firmName: string;
  email: string;
  name: string;
  expiresAt: string;
};

type MockInvitation = ClientInvitation;
const mockInvitationsKey = "ains-synthetic-invitations-v1";

function readMockInvitations(): MockInvitation[] {
  return JSON.parse(
    localStorage.getItem(mockInvitationsKey) ?? "[]",
  ) as MockInvitation[];
}

function writeMockInvitations(invitations: MockInvitation[]) {
  localStorage.setItem(mockInvitationsKey, JSON.stringify(invitations));
}

function syntheticInvitationToken() {
  return `synthetic-invitation-${crypto.randomUUID()}`;
}

function expiresIn72Hours() {
  return new Date(Date.now() + 72 * 60 * 60 * 1000).toISOString();
}

function tokenFromPreview(path: string | null): string | null {
  if (!path) return null;
  return new URL(path, window.location.origin).searchParams.get("token");
}

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
  if (!clientMocksEnabled()) return apiRequest<SessionData>("/auth/session");
  if (localStorage.getItem("ains-synthetic-signed-out") === "true")
    throw new Error("Demo signed out");
  return {
    user: {
      ...mockSession.user,
      role:
        localStorage.getItem("ains-synthetic-role") === "auditor"
          ? "auditor"
          : "client",
    },
  };
}

export async function passwordSignIn(
  email: string,
  password: string,
  mfaCode?: string,
): Promise<SessionData> {
  if (clientMocksEnabled()) {
    const normalized = email.trim().toLowerCase();
    const auditor = normalized === "auditor@example.invalid";
    if ((!auditor && normalized !== "client@example.invalid") || password !== "synthetic-only-password")
      throw new ApiError(401, "Invalid email or password");
    if (auditor && !mfaCode) throw new ApiError(401, "MFA code required");
    if (auditor && mfaCode !== "123456") throw new ApiError(401, "Invalid MFA code");
    localStorage.setItem("ains-synthetic-role", auditor ? "auditor" : "client");
    localStorage.removeItem("ains-synthetic-signed-out");
    return getSession();
  }
  return apiRequest<SessionData>("/auth/password", {
    method: "POST",
    body: JSON.stringify({ email, password, mfa_code: mfaCode || null }),
  });
}

export async function startAuditorMFAEnrollment(
  email: string,
  password: string,
): Promise<AuditorMFAEnrollment> {
  if (USE_MOCKS)
    return {
      secret: "SYNTHETICMFAPREVIEWONLY",
      provisioning_uri:
        "otpauth://totp/Kien%20Solutions:synthetic-auditor?secret=SYNTHETICMFAPREVIEWONLY&issuer=Kien%20Solutions",
      expires_at: new Date(Date.now() + 10 * 60 * 1000).toISOString(),
    };
  return apiRequest<AuditorMFAEnrollment>("/auth/auditor/mfa/enrollment", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export async function confirmAuditorMFAEnrollment(
  email: string,
  password: string,
  code: string,
): Promise<AuditorMFAEnrollmentComplete> {
  if (USE_MOCKS) {
    if (code !== "123456") throw new Error("Use synthetic code 123456.");
    localStorage.setItem("ains-synthetic-role", "auditor");
    localStorage.removeItem("ains-synthetic-signed-out");
    return {
      user: { ...mockSession.user, role: "auditor" },
      recovery_codes: Array.from(
        { length: 10 },
        (_, index) => `DEMO-${String(index + 1).padStart(2, "0")}-NOT-A-REAL-CODE`,
      ),
    };
  }
  return apiRequest<AuditorMFAEnrollmentComplete>(
    "/auth/auditor/mfa/enrollment/confirm",
    {
      method: "POST",
      body: JSON.stringify({ email, password, code }),
    },
  );
}

export async function rotateAuditorMFARecoveryCodes(
  code: string,
): Promise<string[]> {
  if (USE_MOCKS) {
    if (code !== "123456") throw new Error("Use synthetic code 123456.");
    return Array.from(
      { length: 10 },
      (_, index) => `ROTATED-${String(index + 1).padStart(2, "0")}-DEMO-ONLY`,
    );
  }
  const result = await apiRequest<{ recovery_codes: string[] }>(
    "/auth/auditor/mfa/recovery-codes",
    {
      method: "POST",
      body: JSON.stringify({ code }),
    },
  );
  return result.recovery_codes;
}

export async function requestMagicLink(email: string): Promise<void> {
  if (USE_MOCKS)
    throw new Error("Demo mode does not send email. Use Open synthetic demo.");
  await apiRequest<{ status: string }>("/auth/magic-link", {
    method: "POST",
    body: JSON.stringify({ email }),
  });
}

export async function verifyMagicLink(
  token: string,
  mfaCode?: string,
): Promise<SessionData> {
  if (USE_MOCKS)
    throw new Error(
      "Demo mode does not accept sign-in tokens. Use Open synthetic demo.",
    );
  return apiRequest<SessionData>("/auth/magic-link/verify", {
    method: "POST",
    body: JSON.stringify({ token, mfa_code: mfaCode || null }),
  });
}

export async function signOut(): Promise<void> {
  if (clientMocksEnabled()) {
    localStorage.setItem("ains-synthetic-signed-out", "true");
    return;
  }
  await apiRequest<void>("/auth/sign-out", { method: "POST" });
}

export async function getClientInvitations(
  engagementId: string,
): Promise<ClientInvitation[]> {
  if (!USE_MOCKS)
    return apiRequest<ClientInvitation[]>(
      `/auditor/engagements/${encodeURIComponent(engagementId)}/invitations`,
    );
  return readMockInvitations()
    .filter((invitation) => invitation.engagementId === engagementId)
    .map((invitation) => ({ ...invitation, previewPath: null }));
}

export async function createClientInvitation(
  engagementId: string,
  firmId: string,
  firmName: string,
  input: { email: string; name: string },
): Promise<ClientInvitation> {
  if (!USE_MOCKS)
    return apiRequest<ClientInvitation>(
      `/auditor/engagements/${encodeURIComponent(engagementId)}/invitations`,
      {
        method: "POST",
        body: JSON.stringify(input),
      },
    );
  const invitations = readMockInvitations();
  if (
    invitations.some(
      (invitation) => invitation.email === input.email.trim().toLowerCase(),
    )
  )
    throw new Error(
      "This synthetic email already has an invitation. Use resend instead.",
    );
  const token = syntheticInvitationToken();
  const invitation: MockInvitation = {
    id: crypto.randomUUID(),
    firmId,
    engagementId,
    firmName,
    email: input.email.trim().toLowerCase(),
    name: input.name.trim(),
    status: "pending",
    expiresAt: expiresIn72Hours(),
    acceptedAt: null,
    previewPath: `/accept-invitation?token=${encodeURIComponent(token)}`,
  };
  writeMockInvitations([...invitations, invitation]);
  return invitation;
}

export async function resendClientInvitation(
  invitationId: string,
): Promise<ClientInvitation> {
  if (!USE_MOCKS)
    return apiRequest<ClientInvitation>(
      `/auditor/invitations/${encodeURIComponent(invitationId)}/resend`,
      { method: "POST" },
    );
  const invitations = readMockInvitations();
  const invitation = invitations.find((entry) => entry.id === invitationId);
  if (!invitation) throw new Error("Synthetic invitation not found.");
  if (invitation.status === "accepted")
    throw new Error("Accepted invitations cannot be resent.");
  const token = syntheticInvitationToken();
  Object.assign(invitation, {
    status: "pending",
    expiresAt: expiresIn72Hours(),
    previewPath: `/accept-invitation?token=${encodeURIComponent(token)}`,
  });
  writeMockInvitations(invitations);
  return invitation;
}

export async function revokeClientInvitation(
  invitationId: string,
): Promise<ClientInvitation> {
  if (!USE_MOCKS)
    return apiRequest<ClientInvitation>(
      `/auditor/invitations/${encodeURIComponent(invitationId)}/revoke`,
      { method: "POST" },
    );
  const invitations = readMockInvitations();
  const invitation = invitations.find((entry) => entry.id === invitationId);
  if (!invitation) throw new Error("Synthetic invitation not found.");
  if (invitation.status === "accepted")
    throw new Error("Accepted invitations cannot be revoked.");
  invitation.status = "revoked";
  invitation.previewPath = null;
  writeMockInvitations(invitations);
  return invitation;
}

export async function getInvitationDetails(
  token: string,
): Promise<InvitationDetails> {
  if (!USE_MOCKS)
    return apiRequest<InvitationDetails>(
      `/auth/invitations/${encodeURIComponent(token)}`,
    );
  const invitation = readMockInvitations().find(
    (entry) => tokenFromPreview(entry.previewPath) === token,
  );
  if (!invitation || invitation.status !== "pending")
    throw new Error("This synthetic invitation is invalid, expired, or unavailable.");
  if (new Date(invitation.expiresAt).getTime() <= Date.now())
    throw new Error("This synthetic invitation has expired.");
  return {
    firmName: invitation.firmName,
    email: invitation.email,
    name: invitation.name,
    expiresAt: invitation.expiresAt,
  };
}

export async function acceptClientInvitation(
  token: string,
  password: string,
): Promise<SessionData> {
  if (!USE_MOCKS)
    return apiRequest<SessionData>("/auth/invitations/accept", {
      method: "POST",
      body: JSON.stringify({ token, password }),
    });
  const invitations = readMockInvitations();
  const invitation = invitations.find(
    (entry) => tokenFromPreview(entry.previewPath) === token,
  );
  if (!invitation || invitation.status !== "pending")
    throw new Error("This synthetic invitation is invalid, expired, or unavailable.");
  if (password.length < 12)
    throw new Error("Use at least 12 characters for the synthetic password.");
  invitation.status = "accepted";
  invitation.acceptedAt = new Date().toISOString();
  invitation.previewPath = null;
  writeMockInvitations(invitations);
  localStorage.setItem("ains-synthetic-role", "client");
  localStorage.removeItem("ains-synthetic-signed-out");
  return {
    user: {
      id: `synthetic-client-${invitation.id}`,
      email: invitation.email,
      name: invitation.name,
      role: "client",
      firm_id: invitation.firmId,
    },
  };
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

const mockQuestions: Question[] = catalog.requests
  .filter((request) => request.conditions)
  .map((request) => ({
    itemId: request.id,
    sectionTitle: catalog.sections.find(
      (section) => section.id === request.section,
    )!.title,
    question: request.conditions!.question,
    answer: null,
    naReviewState: null,
    whenNo: request.conditions!.when_no,
    representation: null,
  }));

export async function getQuestionnaire(
  engagementId: string,
): Promise<Questionnaire> {
  if (USE_MOCKS) {
    const saved = localStorage.getItem("ains-synthetic-questionnaire-v1");
    return {
      engagementId,
      questions: (saved ? JSON.parse(saved) as Question[] : structuredClone(mockQuestions)).map(question => {
        const item = cloneMockEngagement().sections.flatMap(section => section.items).find(item => item.id === question.itemId);
        return {...question, answer: item?.status === "not_applicable" ? false : question.answer, naReviewState: item?.naReviewState ?? null};
      }),
    };
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
    const { setRequestNA } = await import("./workflow-api");
    for (const answer of answers) {
      const question = current.questions.find(
        (question) => question.itemId === answer.itemId,
      );
      if (!question) throw new Error("Question not found.");
      if (
        !answer.applies &&
        question.whenNo === "representation_required" &&
        !answer.representation
      )
        throw new Error("Confirm the no-activity representation.");
      if (
        question.answer === answer.applies &&
        question.representation ===
          (answer.applies ? null : (answer.representation ?? null))
      )
        continue;
      invalidateMockDecision(answer.itemId, true);
      question.answer = answer.applies;
      await setRequestNA(engagementId, answer.itemId, !answer.applies, "client");
      question.naReviewState = answer.applies ? null : "approved";
      question.representation = answer.applies
        ? null
        : (answer.representation ?? null);

    }
    localStorage.setItem(
      "ains-synthetic-questionnaire-v1",
      JSON.stringify(current.questions),
    );
    return current;
  }
  return apiRequest<Questionnaire>(
    `/engagements/${encodeURIComponent(engagementId)}/questionnaire/answers`,
    { method: "POST", body: JSON.stringify({ answers }) },
  );
}

export type Citation = {
  document?: string;
  page: number;
  quote?: string | null;
};
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
  return apiRequest<AuditorFinding>(
    `/auditor/findings/${encodeURIComponent(findingId)}`,
    {
      method: "PATCH",
      body: JSON.stringify(decision),
    },
  );
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

const DRAFT_REPORT_DOWNLOADS = {
  docx: "kien-draft-report.docx",
  pdf: "kien-draft-report.pdf",
} as const;

function draftReportFilename(format: "docx" | "pdf", disposition: string): string {
  const match = disposition.match(/filename="([^"]+)"/);
  const fromApi = match?.[1] ?? "";
  // API names are kien-<id>-draft-report.docx|pdf. CORS may hide that header.
  if (/^kien-.+-draft-report\.(docx|pdf)$/.test(fromApi)) return fromApi;
  return DRAFT_REPORT_DOWNLOADS[format];
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
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = draftReportFilename(
    format,
    response.headers.get("Content-Disposition") ?? "",
  );
  link.click();
  URL.revokeObjectURL(link.href);
}

export async function getEngagement(): Promise<Engagement> {
  if (USE_MOCKS) {
    await new Promise((resolve) => setTimeout(resolve, 150));
    const data = cloneMockEngagement();
    data.sections = data.sections.map((section) => ({
      ...section,
      items: section.items.filter((item) => item.naReviewState !== "approved" || item.status === "not_applicable"),
    }));
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
  itemId: string | null,
  file: File,
  onProgress: (pct: number) => void,
): Promise<UploadReceipt> {
  if (file.size > MAX_UPLOAD_BYTES) {
    throw new Error(
      `File is larger than ${Math.round(MAX_UPLOAD_BYTES / 1024 / 1024)} MB.`,
    );
  }
  if (USE_MOCKS) {
    const data = cloneMockEngagement();
    const item = data.sections
      .flatMap((section) => section.items)
      .find((item) => item.id === itemId);
    if (itemId !== null && (!item || item.restricted || item.canUpload === false))
      throw new Error("This request cannot accept portal uploads.");
    const suffix = `.${file.name.split(".").pop()?.toLowerCase()}`;
    if (!(item?.allowedEvidenceTypes ?? [".csv", ".doc", ".docx", ".jpeg", ".jpg", ".pdf", ".png", ".tif", ".tiff", ".txt", ".xls", ".xlsx"]).includes(suffix))
      throw new Error("Wrong file type for this request.");
    if (!file.size) throw new Error("File is empty.");
    const sha256 = Array.from(
      new Uint8Array(
        await crypto.subtle.digest("SHA-256", await file.arrayBuffer()),
      ),
    )
      .map((byte) => byte.toString(16).padStart(2, "0"))
      .join("");
    const receipt = {
      id: crypto.randomUUID(),
      name: file.name,
      size: file.size,
      sha256,
      version: "synthetic-1",
      status: "checking" as const,
    };
    if (item) {
      item.files.push({ ...receipt, uploadedAt: new Date().toISOString() });
      item.status = "checking";
      invalidateMockDecision(item.id);
    } else {
      data.unassignedDocuments ??= [];
      data.unassignedDocuments.push({ ...receipt, uploadedAt: new Date().toISOString() });
    }
    saveMockEngagement(data);
    onProgress(100);
    return receipt;
  }

  return await new Promise<UploadReceipt>((resolve, reject) => {
    const request = new XMLHttpRequest();
    request.open(
      "POST",
      `${API_URL}/engagements/${encodeURIComponent(engagementId)}${itemId === null ? "" : `/items/${encodeURIComponent(itemId)}`}/documents`,
    );
    request.withCredentials = true;
    request.timeout = 120000;
    request.ontimeout = () =>
      reject(
        new Error("Upload timed out. Check the checklist before retrying."),
      );
    request.upload.onprogress = (event) => {
      if (event.lengthComputable)
        onProgress((event.loaded / event.total) * 100);
    };
    request.onerror = () =>
      reject(new Error("Upload failed because the API could not be reached."));
    request.onload = () => {
      if (request.status >= 200 && request.status < 300) {
        onProgress(100);
        try {
          resolve(JSON.parse(request.responseText) as UploadReceipt);
        } catch {
          reject(
            new Error(
              "The server did not return a valid receipt. Refresh before retrying.",
            ),
          );
        }
        return;
      }
      let message = `Upload failed (${request.status}).`;
      try {
        const body = JSON.parse(request.responseText) as { detail?: string };
        if (body.detail) message = body.detail;
      } catch {
        // Keep the status-only message for non-JSON responses.
      }
      noteWrongPortal(request.status, message);
      reject(new ApiError(request.status, message));
    };
    const form = new FormData();
    form.append("file", file);
    request.send(form);
  });
}

export type UploadReceipt = {
  id: string;
  name: string;
  size: number;
  sha256: string;
  version: string;
  status: string;
};
