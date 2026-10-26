# Product Requirements Document

## Project context

- **Product:** Kien, by Kien Solutions.
- **Owner:** Unresolved: product decision-maker is not identified in repository documentation. Quentin is the AINS partner and auditor, not necessarily the product owner.
- **Status:** Implementation-grounded working requirements; formal product approval is unresolved.
- **Problem:** Broker-dealer firms and independent auditors need a controlled way to collect AML testing evidence, track human review, document decisions, and prepare reports under FINRA Rule 3310.
- **Target users:** Client firm users and auditors at the audit agency. Quentin is the AINS partner and signing auditor. “Quinton” remains in historical source/docs and rubric placeholders.
- **Desired outcome:** Organized evidence and traceable human review, without making clients interpret audit findings or implying that automated receipt checks constitute an audit.

## MVP scope

- **Must ship (implemented workflow):** Invite-based client and auditor sign-in; firm-scoped engagement workspaces; client questionnaire and neutral 34-item evidence checklist; drag-and-drop multi-file upload without selecting a separate request; auditor document assignment/review, applicability and manual evidence decisions, tasks, internal notes, activity/audit log, report draft and explicit auditor sign-off; recovery and auditor MFA features as implemented.
- **Explicitly excluded or planned:** AI intake that classifies files against 34 checklist items, with auditor confirmation, is planned and not built. SAR (Suspicious Activity Report) pre-screening is planned and must begin with no model runs; SAR material must never be sent to any model. Model inference is not in the application. Production signing is not a cryptographic document signature. Client-side mock demo does not authenticate real users or deliver real files.
- **Constraints:** Web app (Next.js/TypeScript) plus FastAPI API and PostgreSQL 16. The checked-in production infrastructure documents provision an AWS single-host profile, while owner-supplied operating context says Kien runs on OVH; deployment target must be resolved before operations documentation is treated as authoritative. Keep costs low; use synthetic-only examples; enforce server-side tenant boundaries; no external model calls.

## User journeys

1. **Client evidence submission:** An invited client signs in to the firm portal, sees a plain firm card and applicable checklist, answers the questionnaire, drags one or more files into the upload area, confirms upload, and receives receipt/status. No request selection is required during upload. On failure, the UI presents a per-file error and retry path. Restricted checklist items tell the client not to upload their material.
2. **Client status and correction:** The client sees collection progress and neutral document-level feedback (unreadable, wrong period/document, missing pages). They can upload a replacement. Audit findings and internal notes are not client-visible. API/backend errors show retryable loading/error states.
3. **Auditor review:** An authenticated auditor sees assigned engagements, organizes/assigns evidence to checklist items, records applicability, reviews evidence, adds internal notes/tasks, and works through report-readiness blockers. Findings remain drafts pending a human decision. Unassigned engagement access is denied server-side.
4. **Auditor report sign-off:** An assigned auditor reviews the report artifact and explicitly attests to its SHA-256 hash. The API records sign-off and completes the engagement. This records approval of an artifact hash; it is not a cryptographic signature embedded in the report.
5. **Auditor access:** An auditor signs in with email/password. If MFA is enrolled, a second screen requests an authenticator or recovery code. Enrollment, recovery-code rotation, and password recovery use the backend flows. Failures do not grant a session.
6. **Auditor firm workspace management:** Auditors can create/switch workspaces through auditor-only surfaces. Client users receive a plain firm card and cannot switch firms or add workspaces.

## Feature specifications

| ID | User need | Behavior | Acceptance criteria | Priority |
| --- | --- | --- | --- | --- |
| F-01 | Client needs a private firm workspace | Firm-bound user sees only own firm and engagement | Given a client session, another firm’s records and APIs are denied server-side | Must |
| F-02 | Client needs to describe applicable activity | Questionnaire maps answers to checklist applicability; N/A needs auditor review | Client response is persisted; client cannot approve its own N/A; auditor decision is recorded | Must |
| F-03 | Client needs to submit evidence simply | Multi-file drag/drop and file picker, confirm before transfer, server validates file and firm | Upload is attached only to authorized firm/engagement, receipt includes hash/metadata, limits/errors are visible; no request-selection step is required | Must |
| F-04 | Client needs status and correction | Show neutral checklist status and accepted document-level feedback | Client APIs/UI do not expose findings or internal notes; replacements are supported | Must |
| F-05 | Auditor needs assigned-work queue | Portfolio and engagement workspace show assigned engagements, evidence, status, tasks | Unassigned engagements are denied by API regardless of UI route | Must |
| F-06 | Auditor needs traceable human review | Auditor records applicability/evidence decisions, internal notes, draft findings | Actor and change are recorded; finding is not final without auditor action | Must |
| F-07 | Auditor needs a report workflow | Draft generation and readiness blockers; auditor sign-off action | Only assigned auditor can sign off; attestation and artifact hash are required; system records hash and signer | Must |
| F-08 | Auditor access must have stronger authentication | Password sign-in, conditional MFA challenge, enrollment/recovery | Enrolled auditor cannot obtain a session without valid MFA; recovery codes are one-use | Must |
| F-09 | Users need recoverable access | Invitation acceptance, password reset, optional magic-link flow | Expiring, single-use tokens; responses avoid account disclosure where implemented | Must |
| F-10 | Users need a usable responsive interface | Keyboard, phone, light/dark/system themes, loading/empty/error states | Focus is visible, reduced motion honored, theme and responsive navigation work | Must |
| F-11 | Auditors need intake classification assistance | Planned file classification to the 34 checklist items | Planned only: auditor confirmation required before assignment; no inference or authorization is present today | Later |
| F-12 | Auditors need SAR pre-screening | Planned human-only first-stage screening | Planned only: zero model runs for SAR material, and material must never be sent to a model | Later |

## Success measures

- **Metric:** Unresolved: no approved targets or product analytics plan in repository. Candidate operational measures include evidence submission completion, upload error rate, and time to resolve checklist blockers; collect only after privacy and retention decisions.
- **Accessibility/performance:** Responsive use at phone widths, keyboard-operable flows, visible focus, semantic labels, reduced-motion support, and automated browser/accessibility checks exist. No formal WCAG conformance claim or performance budget is established.

## Open decisions

- Deployment source of truth (owner-provided OVH runtime vs checked-in AWS deployment guide and Terraform) — owner: unresolved — needed before operational changes.
- Whether R2/Resend/domain values describe the active production deployment — owner: unresolved; not confirmed by source configuration.
- Product owner, approved design reference, report retention/deletion policy, backup/restore objectives, and success targets — owner: unresolved.
- Audit rubric wording, applicability rules, and allowed evidence types require Quentin’s review; rubric placeholders remain deliberately empty.

## Definition of ready

Feature scope and journey acceptance criteria are implementation-grounded; blockers are named above. Readiness does not mean that unresolved operational decisions are approved or that this workflow establishes regulatory compliance.

## Auditor invoicing (v1)

F-13: Only authenticated auditors can list, create and view invoices for their assigned
client firms. Drafts are editable. Auditors manually mark a draft sent, record dated
payments against a sent invoice, or void an unpaid draft/sent invoice. Partial payments
keep the balance open; full payment sets paid status. Clients have no navigation or API
access. Issue-date range, client and status filters include computed overdue (sent,
past due in UTC, positive balance). No emails, reminders, tax, conversion or payment
processing is included. PDF uses the browser print/save flow. Payment and transition
events provide a base for later follow-up work, which remains unimplemented.


## Numbered checklist N/A

All 34 catalog requests remain visible in numeric order, with auditor-confirmed
`not_applicable` items at the bottom and their original numbers retained. N/A counts
as resolved in collection progress and human review readiness. Only the assigned
auditor can set or undo N/A; clients retain conditional representations pending review.
Undo restores a nullable JSON `na_previous_state` snapshot (revision `a113_checklist_na`).
ClientStatus is non-native VARCHAR, so no PostgreSQL enum alteration is needed.
Set/unset appends to the existing immutable audit chain in the same transaction.
No audit rubric or restricted content is added.


## Editable auditor reports

The existing report template, approved finding drafts, legacy DOCX/PDF generator and
hash-attestation sign-off remain in place. `/auditor/reports` adds persisted editing
per assigned engagement in `engagement_reports` (additive `a114_engagement_reports`).
Firm/period/scope and 34 request statuses are snapshotted server-side on create/save.
Approved findings prefill the narrative; auditors enter per-item report findings.
Restricted items allow metadata only. The native rich-text editor accepts text paste;
the server keeps only formatting tags with no attributes, scripts, URLs or embedded content.
Version checks and row locks prevent lost updates. Finalization requires explicit human
attestation, freezes content and records its SHA-256. Audited reopening permits edits;
prior final hashes remain in the immutable audit chain. Final status does not complete
the engagement, deliver a report, establish a clean opinion or create a cryptographic
signature. Clients receive 403 and have no report navigation; unassigned auditors get 404.
Print view uses the invoice-style browser print/save PDF flow. The idempotent
`python -m app.report_seed` seeds one existing explicitly synthetic demo engagement.
