# Product overview and PRD

> **Source status (2 Nov 2026):** PRs #53–#60 and #64–#72 are merged in the checked-out history through `d822ce1`. The schema head is `a115_user_onboarding`. Merged source does not establish what is deployed. Runtime state was not inspected. Web sign-in is removed for the synthetic demo; backend auth, MFA and tenant isolation remain required. New screen contracts still use mocks; see [frontend inventory](../frontend-inventory.md).

## In one line
Kien (by Kien Solutions) is workflow software for **independent AML testing of broker-dealers under FINRA Rule 3310**. It connects document collection, human evidence review, traceable decisions, report preparation and invoicing.

## Company and people
- **Kien Solutions** — the company (https://kiensolutions.com). "Kien" means the product.
- **Abdullah Ahmed** — owner; directs the build through AI coding agents.
- **Quentin Koch** — partner and credentialed auditor. Approves findings and signs reports. (Repo history spells it "Quinton"; current spelling is Quentin.)
- Earlier internal name: **AINS** / "AML Audit OS" (Notion hub, repo name `ains-platform`, cookie `ains_session`).

## Business context (from Notion hub, Sep 2026)
- Kien Solutions sells the signed independent AML test as a service; the software does the mechanical work, Quentin judges and signs.
- First market: small limited-purpose securities firms (M&A advisory, private placement, introducing brokers; many are Capital Acquisition Brokers tested every two years under CAB Rule 331).
- Target pricing discussed: ~$4,500 small BD test, $6,500 with customer accounts (proposed, not confirmed in repo).

## Users and roles
| Role | Who | What they do |
| --- | --- | --- |
| **Client** | Broker-dealer staff, invited by an auditor | Answer questionnaire, upload evidence, mark items N/A, see neutral status and document feedback |
| **Auditor** | Quentin and other auditors | Manage workspaces, assign/review evidence, notes, tasks, pipeline, reports, invoices, audit log |
There is **no firm-admin role** and **no public sign-up** (invite only).

## Core principles
1. Collection status is not an audit conclusion. Client feedback only describes document issues (unreadable, wrong period, wrong document, missing pages) — never findings.
2. Findings stay drafts until a human auditor approves. Only an auditor can finalize/sign a report.
3. Tenant isolation is enforced on the server (`firm_id` + auditor assignment). UI gates are not security.
4. Restricted/SAR items: clients are told not to upload; human-only handling; never sent to a model.
5. Synthetic data only for demos and tests.

Backend-authenticated target journeys below require restoration of the removed web auth flows. The current synthetic demo does not sign users in. New screen behavior is tracked in [frontend inventory](../frontend-inventory.md).

## User journeys
1. **Client evidence submission** — invited client signs in at their firm portal (`<firm>.kiensolutions.com`), answers the questionnaire, drags files into one upload area (no need to pick a checklist item), gets a receipt with SHA-256 hash.
2. **Client status and correction** — sees progress and neutral feedback, uploads replacements.
3. **Client N/A** — marks items not applicable (and can undo) directly. This matches how firms run the process today.
4. **Auditor review** — sees assigned engagements, assigns evidence to items, records applicability and evidence decisions, notes, tasks, report-readiness blockers.
5. **Auditor report** — (Editable reports and the legacy DOCX/PDF workflow are both merged.) edits the report, finalizes with explicit attestation (records SHA-256 of content), can reopen (audited). Print to PDF via browser.
6. **Auditor access** — email/password, TOTP MFA when enrolled, recovery codes.
7. **Workspaces** — auditors create/switch firm workspaces; clients see a plain firm card only.
8. **Invoicing** — auditor-only ledger.
9. **First sign-in walkthrough** — three-step tour shown once per account, ever.

## Requirements table (from docs/PRD.md)
| ID | Need | Priority / status |
| --- | --- | --- |
| F-01 | Private firm workspace | Must / built |
| F-02 | Client applicability (N/A) — client and assigned auditor can set/undo | Must / merged (#55, #58) |
| F-03 | Multi-file upload, no request selection | Must / built |
| F-04 | Neutral status and replacements | Must / built |
| F-05 | Auditor assigned-work queue | Must / built |
| F-06 | Traceable human review | Must / built |
| F-07 | Report workflow + sign-off | Must / merged legacy and editable reports; new tabbed assembly remains mock |
| F-08 | Auditor MFA | Must / built |
| F-09 | Invitations, password reset, magic link | Must / built |
| F-10 | Responsive, keyboard, themes | Must / built |
| F-11 | AI intake classification | Later / not built |
| F-12 | SAR pre-screen (zero model runs) | Later / not built |
| F-13 | Auditor invoicing v1 | Merged (#53, #54) |

## Explicitly not in the product (today)
Model inference in `app/` (blocked by `tests/test_workflow_boundary.py`), cryptographic report signatures, payment processing, invoice emails, public sign-up, Supabase.

## Unresolved (per repo docs)
Security owner, audit rubric wording (Quentin must supply; placeholders intentionally empty), retention/deletion policy, backup objectives, success metrics.
