/**
 * Frontend data contracts for the new audit screens.
 * Functions returning these shapes live in `src/lib/api/*`; remaining mock-only
 * contracts carry `// TODO(backend)`. Real APIs return these camelCase shapes.
 */

export type Conclusion = "pass" | "partial" | "fail" | "na";
export type Severity = "low" | "moderate" | "high" | "critical";
export type FindingStatus =
  | "draft"
  | "approved"
  | "issued"
  | "responded"
  | "closed";

export type Contact = {
  id: string;
  name: string;
  title: string;
  email: string;
  phone: string;
  primary: boolean;
};

export type EngagementRef = {
  engagementId: string;
  period: string;
  status: "active" | "complete";
  signedOn: string | null;
};

export type ClientProfile = {
  id: string;
  firmName: string;
  firmType: string;
  crd: string;
  clearing: string;
  state: string;
  onboardedOn: string;
  contacts: Contact[];
  engagements: EngagementRef[];
};

export type EngagementSummary = {
  id: string;
  clientId: string;
  firmName: string;
  period: string;
  stage: string;
  due: string | null;
  lead: string;
  reviewer: string;
  partner: string;
};

export type ChecklistTest = {
  requestId: string;
  title: string;
  section: string;
  restricted: boolean;
  conclusion: Conclusion | null;
  updatedAt: string | null;
};

export type EngagementDocument = {
  id: string;
  engagementId: string;
  requestId: string;
  name: string;
  sha256: string;
  pages: number;
  uploadedAt: string;
  uploadedBy: string;
  /** Document-level feedback only (unreadable, wrong period, missing pages). Never findings. */
  feedback: string | null;
};

export type Workpaper = {
  requestId: string;
  procedure: string;
  evidenceIds: string[];
  conclusion: Conclusion | null;
  preparer: string;
  preparedAt: string | null;
  reviewer: string;
  reviewedAt: string | null;
};

export type SampleResult = "pending" | "pass" | "exception";
export type SampleItem = {
  id: string;
  reference: string;
  result: SampleResult;
  note: string;
};
export type SampleSet = {
  id: string;
  engagementId: string;
  area: string;
  requestId: string | null;
  population: number;
  sampleSize: number;
  method: string;
  items: SampleItem[];
};

export type Citation = { document: string; page: number };
export type Finding = {
  id: string;
  engagementId: string;
  title: string;
  rule: string;
  condition: string;
  cause: string;
  effect: string;
  recommendation: string;
  severity: Severity;
  citations: Citation[];
  managementResponse: string;
  respondedAt: string | null;
  status: FindingStatus;
  updatedAt: string;
};

export type ReportSection = { id: string; title: string; body: string };
export type ReportDraft = {
  engagementId: string;
  sections: ReportSection[];
  generatedAt: string;
};

export type SignoffState = {
  engagementId: string;
  reviewer: { name: string; approvedAt: string | null; note: string };
  partner: {
    name: string;
    signedAt: string | null;
    fingerprint: string | null;
  };
  completedAt: string | null;
};

export type IndependenceRecord = {
  engagementId: string;
  answers: { id: string; question: string; answer: "yes" | "no" | null }[];
  conflicts: string;
  safeguards: string;
  conclusion: "independent" | "safeguards_required" | "not_independent" | null;
  declaredBy: string | null;
  declaredAt: string | null;
};

export type ActivityEntry = {
  id: string;
  engagementId: string;
  at: string;
  actor: string;
  action: string;
};

export type TeamRole = "partner" | "reviewer" | "auditor" | "admin";
export type TeamMember = {
  id: string;
  name: string;
  email: string;
  role: TeamRole;
  status: "active" | "invited";
};
export type FirmBranding = { name: string; logoDataUrl: string | null; tagline: string };
export type RubricItem = {
  requestId: string;
  title: string;
  section: string;
  criteria: string;
  enabled: boolean;
};
export type RequestTemplate = {
  id: string;
  name: string;
  kind: "clearing" | "introducing" | "retail" | "custom";
  description: string;
  requestIds: string[];
};

export type Notification = {
  id: string;
  at: string;
  title: string;
  detail: string;
  href: string;
  kind: "deadline" | "upload" | "finding" | "signoff" | "invoice";
  read: boolean;
};

export type SearchHit = {
  id: string;
  kind: "Client" | "Engagement" | "Finding" | "Request" | "Document";
  title: string;
  detail: string;
  href: string;
};

/** What the client sees: only what the auditor chose to write. Never severity, condition, cause, effect or drafts. */
export type ResponseRequest = {
  id: string;
  title: string;
  requestText: string;
  status: "open" | "responded";
  response: string;
  respondedAt: string | null;
  releasedAt: string;
};
export type ClientPortalReport = {
  id: string;
  period: string;
  available: boolean;
  signedOn: string | null;
  signedBy: string | null;
  fingerprint: string | null;
  sections: ReportSection[];
};
export type ClientPortalInvoice = {
  id: string;
  number: string;
  issued: string;
  due: string;
  amountCents: number;
  status: "sent" | "paid" | "overdue";
};
