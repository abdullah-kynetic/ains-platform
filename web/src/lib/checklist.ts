export type ClientStatus =
  | "requested"
  | "checking"
  | "action_needed_reupload"
  | "action_needed_more"
  | "with_auditor"
  | "accepted_for_testing"
  | "restricted_do_not_upload";

type StatusTone = "default" | "brand" | "success" | "warning" | "danger" | "info";

export const STATUS_META: Record<
  ClientStatus,
  { label: string; help: string; tone: StatusTone }
> = {
  requested: {
    label: "Requested",
    help: "Please upload this document.",
    tone: "default",
  },
  checking: {
    label: "Checking",
    help: "We are checking that the uploaded document is usable.",
    tone: "info",
  },
  action_needed_reupload: {
    label: "Please re-upload",
    help: "The file could not be used and needs to be uploaded again.",
    tone: "warning",
  },
  action_needed_more: {
    label: "More needed",
    help: "Additional pages or documents are needed.",
    tone: "warning",
  },
  with_auditor: {
    label: "With auditor",
    help: "The document is with the auditor.",
    tone: "brand",
  },
  accepted_for_testing: {
    label: "Accepted for testing",
    help: "The document is usable for testing. This is not an audit conclusion.",
    tone: "success",
  },
  restricted_do_not_upload: {
    label: "Do not upload",
    help: "This restricted item is handled directly with the auditor. Do not upload it here.",
    tone: "danger",
  },
};

export const UPLOADABLE = new Set<ClientStatus>([
  "requested",
  "action_needed_reupload",
  "action_needed_more",
]);

export type UploadedFile = {
  id: string;
  name: string;
  size: number;
  uploadedAt: string;
};

export type ChecklistItem = {
  id: string;
  requestId: string;
  restricted: boolean;
  allowedEvidenceTypes: string[];
  title: string;
  description?: string;
  status: ClientStatus;
  reason?: string;
  files: UploadedFile[];
};

export type ChecklistSection = {
  id: string;
  title: string;
  description?: string;
  items: ChecklistItem[];
};

export type Engagement = {
  id: string;
  firmName: string;
  engagementType: string;
  reviewPeriod: { start: string; end: string };
  dueDate: string;
  sections: ChecklistSection[];
};

export function countByStatus(engagement: Engagement): Record<ClientStatus, number> {
  const counts = Object.fromEntries(
    Object.keys(STATUS_META).map((status) => [status, 0]),
  ) as Record<ClientStatus, number>;
  for (const section of engagement.sections) {
    for (const item of section.items) counts[item.status] += 1;
  }
  return counts;
}

export function progressOf(engagement: Engagement): { done: number; total: number; pct: number } {
  const items = engagement.sections
    .flatMap((section) => section.items)
    .filter((item) => item.status !== "restricted_do_not_upload");
  const done = items.filter((item) =>
    ["checking", "with_auditor", "accepted_for_testing"].includes(item.status),
  ).length;
  return { done, total: items.length, pct: items.length ? (done / items.length) * 100 : 0 };
}
