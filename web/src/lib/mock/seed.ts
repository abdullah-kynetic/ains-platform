/**
 * Synthetic seed data. Fictional firms, people and documents only: no real client
 * data and no SAR content. The real backend replaces everything in `src/lib/mock`.
 */
import catalog from "../../../.generated/catalog.json";
import type {
  ActivityEntry,
  ClientProfile,
  ChecklistTest,
  Conclusion,
  EngagementDocument,
  EngagementSummary,
  Finding,
  FirmBranding,
  IndependenceRecord,
  Notification,
  RequestTemplate,
  RubricItem,
  SampleSet,
  SignoffState,
  TeamMember,
  Workpaper,
} from "../api/types";

export const CURRENT_USER = "Dana Whitfield";
export const REVIEWER = "Priya Raman";
export const PARTNER = "Quentin";

const contact = (id: string, name: string, title: string, domain: string, primary = false) => ({
  id,
  name,
  title,
  email: `${name.toLowerCase().replace(/[^a-z]+/g, ".")}@${domain}`,
  phone: "555-0100",
  primary,
});

export const seedClients = (): ClientProfile[] => [
  {
    id: "cl-001", firmName: "Example Securities LLC (synthetic)", firmType: "Introducing broker-dealer", crd: "SYN-10001", clearing: "Fully disclosed, Aldrin Clearing", state: "NY", onboardedOn: "2024-09-03",
    contacts: [contact("ct-1", "Maya Okafor", "Chief Compliance Officer", "example-securities.test", true), contact("ct-2", "Jonah Reyes", "AML Officer", "example-securities.test")],
    engagements: [
      { engagementId: "eng-synthetic-001", period: "Jan–Dec 2025", status: "active", signedOn: null },
      { engagementId: "eng-2024-001", period: "Jan–Dec 2024", status: "complete", signedOn: "2025-12-12" },
    ],
  },
  {
    id: "cl-002", firmName: "Northstar Brokerage Inc. (synthetic)", firmType: "Retail broker-dealer", crd: "SYN-10002", clearing: "Fully disclosed, Aldrin Clearing", state: "TX", onboardedOn: "2026-10-12",
    contacts: [contact("ct-3", "Elena Marsh", "Chief Compliance Officer", "northstar.test", true)],
    engagements: [{ engagementId: "eng-synthetic-002", period: "Jan–Dec 2025", status: "active", signedOn: null }],
  },
  {
    id: "cl-003", firmName: "Meridian Capital Markets (synthetic)", firmType: "Institutional broker-dealer", crd: "SYN-10003", clearing: "Self-clearing", state: "IL", onboardedOn: "2025-02-18",
    contacts: [contact("ct-4", "Tomas Brandt", "General Counsel", "meridian.test", true), contact("ct-5", "Ines Calloway", "AML Officer", "meridian.test")],
    engagements: [{ engagementId: "eng-synthetic-003", period: "Jan–Dec 2025", status: "active", signedOn: null }],
  },
  {
    id: "cl-004", firmName: "Harborview Securities (synthetic)", firmType: "Retail broker-dealer", crd: "SYN-10004", clearing: "Fully disclosed, Aldrin Clearing", state: "MA", onboardedOn: "2024-06-20",
    contacts: [contact("ct-6", "Priyanka Desai", "Chief Compliance Officer", "harborview.test", true)],
    engagements: [
      { engagementId: "eng-synthetic-004", period: "Jan–Dec 2025", status: "active", signedOn: null },
      { engagementId: "eng-2024-004", period: "Jan–Dec 2024", status: "complete", signedOn: "2025-11-20" },
    ],
  },
  {
    id: "cl-005", firmName: "Summit BD Partners (synthetic)", firmType: "Introducing broker-dealer", crd: "SYN-10005", clearing: "Fully disclosed, Aldrin Clearing", state: "CO", onboardedOn: "2025-04-02",
    contacts: [contact("ct-7", "Gareth Lund", "Chief Compliance Officer", "summit-bd.test", true)],
    engagements: [{ engagementId: "eng-synthetic-005", period: "Jan–Dec 2025", status: "active", signedOn: null }],
  },
  {
    id: "cl-006", firmName: "Cedar Ridge Financial (synthetic)", firmType: "Introducing broker-dealer", crd: "SYN-10006", clearing: "Fully disclosed, Aldrin Clearing", state: "OR", onboardedOn: "2025-07-09",
    contacts: [contact("ct-8", "Noor Haddad", "Chief Compliance Officer", "cedarridge.test", true)],
    engagements: [{ engagementId: "eng-synthetic-006", period: "Jan–Dec 2025", status: "active", signedOn: null }],
  },
  {
    id: "cl-007", firmName: "Bluewater Securities Group (synthetic)", firmType: "Self-clearing broker-dealer", crd: "SYN-10007", clearing: "Self-clearing", state: "FL", onboardedOn: "2024-03-15",
    contacts: [contact("ct-9", "Luis Ferreira", "Chief Compliance Officer", "bluewater.test", true)],
    engagements: [{ engagementId: "eng-synthetic-007", period: "Jan–Dec 2025", status: "complete", signedOn: "2026-10-17" }],
  },
];

const stageLabel: Record<string, string> = {
  "eng-synthetic-001": "Document collection", "eng-synthetic-002": "Intake", "eng-synthetic-003": "Document collection",
  "eng-synthetic-004": "Auditor review", "eng-synthetic-005": "Report drafting", "eng-synthetic-006": "Awaiting signature", "eng-synthetic-007": "Complete",
};
const dues: Record<string, string> = {
  "eng-synthetic-001": "2026-12-15", "eng-synthetic-002": "2026-12-18", "eng-synthetic-003": "2026-12-22",
  "eng-synthetic-004": "2026-11-26", "eng-synthetic-005": "2026-11-14", "eng-synthetic-006": "2026-11-08", "eng-synthetic-007": "2026-10-17",
};

export const seedEngagements = (): EngagementSummary[] =>
  seedClients().map((client, index) => {
    const id = `eng-synthetic-00${index + 1}`;
    return { id, clientId: client.id, firmName: client.firmName, period: "Jan–Dec 2025", stage: stageLabel[id], due: dues[id], lead: CURRENT_USER, reviewer: REVIEWER, partner: PARTNER };
  });

/* ---------- checklist ---------- */
const sectionTitle = new Map(catalog.sections.map((s) => [s.id, s.title]));
export const sectionName = (id: string) => sectionTitle.get(id) ?? id;

const progressByEngagement: Record<string, number> = {
  "eng-synthetic-001": 14, "eng-synthetic-002": 0, "eng-synthetic-003": 9, "eng-synthetic-004": 28,
  "eng-synthetic-005": 34, "eng-synthetic-006": 34, "eng-synthetic-007": 34,
};
const cycle: Conclusion[] = ["pass", "pass", "partial", "pass", "fail", "pass", "pass", "partial", "pass", "pass"];

export const seedChecklist = (engagementId: string): ChecklistTest[] => {
  const done = progressByEngagement[engagementId] ?? 0;
  return catalog.requests.map((request, index) => {
    const restricted = request.restricted;
    const naItem = [10, 14, 15, 21, 23].includes(index) && done > 0;
    const conclusion: Conclusion | null = index >= done && !naItem ? null : naItem ? "na" : restricted ? "pass" : cycle[index % cycle.length];
    return { requestId: request.id, title: request.title, section: request.section, restricted, conclusion, updatedAt: conclusion ? "2026-10-28T14:00:00.000Z" : null };
  });
};

/* ---------- documents ---------- */
const doc = (n: number, requestId: string, name: string, pages: number, feedback: string | null = null): EngagementDocument => ({
  id: `doc-001-${n}`, engagementId: "eng-synthetic-001", requestId, name, sha256: `${(n * 7919 + 104729).toString(16).padStart(8, "0")}c4a1e9d03b57f2a6180d94ce7b31a5f0928d6e4c1b7a30f59d82e61c`.slice(0, 64),
  pages, uploadedAt: `2026-10-${String(10 + n).padStart(2, "0")}T15:20:00.000Z`, uploadedBy: "Maya Okafor", feedback,
});
export const seedDocuments = (): EngagementDocument[] => [
  doc(1, "AML-BD-001", "AML-Program-WSPs-2025.pdf", 64),
  doc(2, "AML-BD-002", "Signed-Representation-Letter.pdf", 2),
  doc(3, "AML-BD-003", "AML-Training-Roster-2025.xlsx", 6),
  doc(4, "AML-BD-004", "Clearing-Exception-Reports-Q1-Q4.pdf", 38, "Pages 14–15 are missing from the Q3 report. Please upload a complete copy."),
  doc(5, "AML-BD-009", "CDD-Files-Selected-Accounts.pdf", 51),
  doc(6, "AML-BD-014", "Internal-AML-Test-2025.docx", 17),
  doc(7, "AML-BD-020", "Risk-Assessment-2025.pdf", 12, "The document covers 2024. Please upload the 2025 period."),
  doc(8, "AML-BD-026", "Government-Requests-Log.xlsx", 3),
];

/* ---------- workpapers ---------- */
export const seedWorkpapers = (): Workpaper[] => [
  { requestId: "AML-BD-001", procedure: "Compared the written AML program with the elements required by FINRA Rule 3310(a)–(e) and confirmed annual board or senior-management approval.", evidenceIds: ["doc-001-1"], conclusion: "pass", preparer: CURRENT_USER, preparedAt: "2026-10-26T16:00:00.000Z", reviewer: REVIEWER, reviewedAt: "2026-10-28T10:30:00.000Z" },
  { requestId: "AML-BD-003", procedure: "Agreed training roster to the employee census; confirmed all in-scope staff completed annual training.", evidenceIds: ["doc-001-3"], conclusion: "partial", preparer: CURRENT_USER, preparedAt: "2026-10-27T11:15:00.000Z", reviewer: "", reviewedAt: null },
];

/* ---------- samples ---------- */
export const seedSamples = (): SampleSet[] => [
  {
    id: "smp-1", engagementId: "eng-synthetic-001", area: "Transaction-monitoring alerts closed", requestId: "AML-BD-004", population: 412, sampleSize: 25, method: "Random, seeded (ID 4821)",
    items: Array.from({ length: 25 }, (_, i) => ({ id: `smp-1-${i + 1}`, reference: `ALERT-2025-${String(1000 + i * 13)}`, result: i < 18 ? ("pass" as const) : i === 19 || i === 22 ? ("exception" as const) : i < 21 ? ("pass" as const) : ("pending" as const), note: i === 19 ? "Closed without documented rationale." : i === 22 ? "Review exceeded the 30-day escalation limit." : "" })),
  },
  {
    id: "smp-2", engagementId: "eng-synthetic-001", area: "New customer CIP files", requestId: "AML-BD-009", population: 186, sampleSize: 15, method: "Stratified by account type",
    items: Array.from({ length: 15 }, (_, i) => ({ id: `smp-2-${i + 1}`, reference: `CIP-ACCT-${String(7000 + i * 11)}`, result: "pending" as const, note: "" })),
  },
];

/* ---------- findings ---------- */
const finding = (n: number, f: Partial<Finding> & Pick<Finding, "title" | "rule" | "condition" | "cause" | "effect" | "recommendation" | "severity" | "status">): Finding => ({
  id: `fnd-${n}`, engagementId: "eng-synthetic-001", citations: [], managementResponse: "", respondedAt: null, updatedAt: "2026-10-29T12:00:00.000Z", ...f,
});
export const seedFindings = (): Finding[] => [
  finding(1, {
    title: "Transaction-monitoring alerts closed without documented rationale", rule: "FINRA Rule 3310(a); BSA — suspicious activity monitoring pillar",
    condition: "Two of 25 sampled alerts were closed without a documented rationale; one review exceeded the firm’s 30-day escalation limit.",
    cause: "The alert-closure template does not require a free-text rationale before closing.", effect: "Reviewers cannot evidence why activity was judged not suspicious, weakening the firm’s monitoring record.",
    recommendation: "Make the rationale field mandatory and add a monthly supervisory review of aged alerts.", severity: "high",
    citations: [{ document: "Clearing-Exception-Reports-Q1-Q4.pdf", page: 22 }, { document: "AML-Program-WSPs-2025.pdf", page: 31 }],
    status: "issued", managementResponse: "",
  }),
  finding(2, {
    title: "AML risk assessment not updated for the review period", rule: "FINRA Rule 3310(a); FinCEN CDD rule — risk-based procedures",
    condition: "The risk assessment provided covers 2024 and does not reflect the 2025 product launch.", cause: "Annual refresh is not on the compliance calendar.",
    effect: "Controls may not match the firm’s current risk profile.", recommendation: "Refresh the assessment annually and after material business changes; record approval.", severity: "moderate",
    citations: [{ document: "Risk-Assessment-2025.pdf", page: 3 }], status: "responded",
    managementResponse: "We agree. The assessment will be refreshed by 12/31 and added to the compliance calendar.", respondedAt: "2026-10-30T09:40:00.000Z",
  }),
  finding(3, {
    title: "Training records missing for two new hires", rule: "FINRA Rule 3310(e) — ongoing training", condition: "Two employees hired in Q3 have no recorded AML training.",
    cause: "Onboarding checklist omits AML training.", effect: "Staff may handle accounts without required training.", recommendation: "Add AML training to onboarding and track completion within 30 days.",
    severity: "low", citations: [{ document: "AML-Training-Roster-2025.xlsx", page: 4 }], status: "draft",
  }),
];

/* ---------- independence, sign-off, activity ---------- */
export const independenceQuestions = [
  "Do any engagement team members hold a financial interest in the client?",
  "Has any team member been employed by or served on the board of the client in the last 24 months?",
  "Do we provide, or have we provided, AML program design or operational services to the client?",
  "Does any team member have a family or close personal relationship with a client officer?",
  "Are our fees contingent on the outcome of the test?",
];
const declared = (id: string) => ["001", "004", "005", "006", "007"].some((n) => id.endsWith(n));
export const seedIndependence = (engagementId: string): IndependenceRecord => ({
  engagementId,
  answers: independenceQuestions.map((question, i) => ({ id: `q${i + 1}`, question, answer: declared(engagementId) ? "no" : null })),
  conflicts: "", safeguards: "",
  conclusion: declared(engagementId) ? "independent" : null,
  declaredBy: declared(engagementId) ? CURRENT_USER : null,
  declaredAt: declared(engagementId) ? "2026-10-12T09:00:00.000Z" : null,
});
export const seedSignoff = (engagementId: string): SignoffState => ({
  engagementId,
  reviewer: { name: REVIEWER, approvedAt: ["eng-synthetic-006", "eng-synthetic-007"].includes(engagementId) ? "2026-10-15T10:00:00.000Z" : null, note: "" },
  partner: { name: PARTNER, signedAt: engagementId === "eng-synthetic-007" ? "2026-10-17T13:00:00.000Z" : null, fingerprint: engagementId === "eng-synthetic-007" ? "9f2c1ad04b6e8a35d17f90c2e4b8a61d3c5f7e0928b4a6d1c3e5f70a92b8d4e6" : null },
  completedAt: engagementId === "eng-synthetic-007" ? "2026-10-17T13:05:00.000Z" : null,
});
export const seedActivity = (engagementId: string): ActivityEntry[] => [
  { id: "a1", engagementId, at: "2026-10-30T09:40:00.000Z", actor: "Maya Okafor (client)", action: "Submitted a management response to “AML risk assessment not updated”." },
  { id: "a2", engagementId, at: "2026-10-29T12:00:00.000Z", actor: CURRENT_USER, action: "Issued finding “Transaction-monitoring alerts closed without documented rationale”." },
  { id: "a3", engagementId, at: "2026-10-28T10:30:00.000Z", actor: REVIEWER, action: "Reviewed workpaper for AML-BD-001 (Pass)." },
  { id: "a4", engagementId, at: "2026-10-27T11:15:00.000Z", actor: CURRENT_USER, action: "Prepared workpaper for AML-BD-003 (Partial)." },
  { id: "a5", engagementId, at: "2026-10-22T15:20:00.000Z", actor: "Maya Okafor (client)", action: "Uploaded Government-Requests-Log.xlsx for AML-BD-026." },
  { id: "a6", engagementId, at: "2026-10-12T09:00:00.000Z", actor: CURRENT_USER, action: "Declared independence: no conflicts." },
];

/* ---------- firm ---------- */
export const seedTeam = (): TeamMember[] => [
  { id: "tm-1", name: PARTNER, email: "quentin@kien-synthetic.test", role: "partner", status: "active" },
  { id: "tm-2", name: REVIEWER, email: "priya.raman@kien-synthetic.test", role: "reviewer", status: "active" },
  { id: "tm-3", name: CURRENT_USER, email: "dana.whitfield@kien-synthetic.test", role: "auditor", status: "active" },
  { id: "tm-4", name: "Abdullah (admin)", email: "admin@kien-synthetic.test", role: "admin", status: "active" },
  { id: "tm-5", name: "Chris Lindgren", email: "chris.lindgren@kien-synthetic.test", role: "auditor", status: "invited" },
];
export const seedBranding = (): FirmBranding => ({ name: "Kien Solutions", logoDataUrl: null, tagline: "Independent AML testing for broker-dealers" });
export const seedRubric = (): RubricItem[] =>
  catalog.requests.map((r) => ({ requestId: r.id, title: r.title, section: r.section, criteria: "", enabled: true }));

const ids = catalog.requests.map((r) => r.id);
export const seedTemplates = (): RequestTemplate[] => [
  { id: "tpl-all", name: "Full Rule 3310 request list", kind: "custom", description: "All 34 requests, the default for a new engagement.", requestIds: ids },
  { id: "tpl-intro", name: "Introducing broker-dealer", kind: "introducing", description: "Fully disclosed firms. Clearing-firm reports and clearing-firm exception reviews stay in scope; custody-only requests are dropped.", requestIds: ids.filter((id) => !["AML-BD-015", "AML-BD-023", "AML-BD-031"].includes(id)) },
  { id: "tpl-retail", name: "Retail broker-dealer", kind: "retail", description: "Retail customer base: emphasises CIP, CDD files, money movement and complaints.", requestIds: ids.filter((id) => !["AML-BD-011", "AML-BD-022", "AML-BD-024"].includes(id)) },
  { id: "tpl-clearing", name: "Self-clearing broker-dealer", kind: "clearing", description: "Adds transaction and system controls; omits clearing-firm reports.", requestIds: ids.filter((id) => id !== "AML-BD-004") },
];

/* ---------- notifications ---------- */
export const seedNotifications = (): Notification[] => [
  { id: "n1", at: "2026-10-30T09:40:00.000Z", title: "Management response received", detail: "Example Securities responded to “AML risk assessment not updated”.", href: "/auditor/engagements/eng-synthetic-001/findings", kind: "finding", read: false },
  { id: "n2", at: "2026-10-29T15:05:00.000Z", title: "Report ready for signature", detail: "Cedar Ridge Financial is awaiting Quentin’s sign-off.", href: "/auditor/engagements/eng-synthetic-006/sign-off", kind: "signoff", read: false },
  { id: "n3", at: "2026-10-28T08:00:00.000Z", title: "Deadline in 7 days", detail: "Cedar Ridge Financial report due 8 Nov.", href: "/auditor/engagements/eng-synthetic-006", kind: "deadline", read: false },
  { id: "n4", at: "2026-10-22T15:20:00.000Z", title: "New upload", detail: "Example Securities uploaded Government-Requests-Log.xlsx.", href: "/auditor/engagements/eng-synthetic-001/documents", kind: "upload", read: true },
  { id: "n5", at: "2026-10-20T10:00:00.000Z", title: "Invoice overdue", detail: "Invoice for Bluewater Securities Group is past due.", href: "/auditor/invoices", kind: "invoice", read: true },
];
