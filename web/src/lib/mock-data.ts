import type { Engagement } from "./checklist";

export const MOCK_ENGAGEMENT: Engagement = {
  id: "eng-synthetic-001",
  firmName: "Example Securities LLC",
  engagementType: "FINRA Rule 3310 Independent AML Test",
  reviewPeriod: { start: "2025-01-01", end: "2025-12-31" },
  dueDate: "2026-02-15",
  sections: [
    {
      id: "governance",
      title: "AML program and governance",
      description: "Core policies, approvals, and responsibility records.",
      items: [
        {
          id: "aml-program",
          title: "Written AML program",
          description: "The current written AML program and approval record.",
          status: "accepted_for_testing",
          files: [
            {
              id: "file-synthetic-001",
              name: "synthetic-aml-program.pdf",
              size: 428_100,
              uploadedAt: "2026-01-10T18:00:00Z",
            },
          ],
        },
        {
          id: "aml-officer",
          title: "AML compliance officer designation",
          status: "with_auditor",
          files: [
            {
              id: "file-synthetic-002",
              name: "synthetic-aml-officer-designation.pdf",
              size: 92_420,
              uploadedAt: "2026-01-11T18:00:00Z",
            },
          ],
        },
      ],
    },
    {
      id: "operations",
      title: "Customer and transaction records",
      description: "Records used to confirm the requested period is complete and readable.",
      items: [
        {
          id: "customer-list",
          title: "Customer account list",
          description: "Customer accounts active during the review period.",
          status: "checking",
          files: [
            {
              id: "file-synthetic-003",
              name: "synthetic-customer-list.csv",
              size: 18_902,
              uploadedAt: "2026-01-12T18:00:00Z",
            },
          ],
        },
        {
          id: "training-records",
          title: "AML training records",
          description: "Training materials and completion records for the review period.",
          status: "action_needed_more",
          reason: "The upload is missing the employee completion record for the review period.",
          files: [
            {
              id: "file-synthetic-004",
              name: "synthetic-training-materials.pdf",
              size: 311_228,
              uploadedAt: "2026-01-12T18:00:00Z",
            },
          ],
        },
        {
          id: "monitoring-alerts",
          title: "Transaction monitoring alert log",
          description: "The alert log for the review period, without SAR narratives.",
          status: "requested",
          files: [],
        },
        {
          id: "id-documents",
          title: "Sample identity verification documents",
          status: "action_needed_reupload",
          reason: "Several pages are unreadable. Please upload a clearer copy.",
          files: [],
        },
      ],
    },
    {
      id: "restricted",
      title: "Restricted materials",
      description: "These materials are coordinated directly with the auditor.",
      items: [
        {
          id: "sar-material",
          title: "SAR-related material",
          description: "Quinton will coordinate this item through the restricted process.",
          status: "restricted_do_not_upload",
          files: [],
        },
      ],
    },
  ],
};

export function cloneMockEngagement(): Engagement {
  return structuredClone(MOCK_ENGAGEMENT);
}
