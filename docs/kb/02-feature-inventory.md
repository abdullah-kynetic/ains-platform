# Feature inventory (as built)

> **Source status (2 Nov 2026):** PRs #53–#60 and #64–#72 are merged in the checked-out history through `d822ce1`. The schema head is `a116_client_profiles`. Merged source does not establish what is deployed. Runtime state was not inspected. Web sign-in is removed for the synthetic demo; backend auth, MFA and tenant isolation remain required. New screen contracts still use mocks; see [frontend inventory](../frontend-inventory.md).

Status key: **Merged** = present in checked-out source; **Mock** = UI with synthetic data; **Planned** = not built. Deployment is unverified. No status here claims a live release.

New clients, engagement summaries/tabs, workpapers, samples, structured findings, report assembly/sign-off, independence, firm settings, notifications/search and client result pages are **Mock**. See [frontend inventory](../frontend-inventory.md) for contracts. Legacy backend routes below remain implemented independently.

## Client workspace
| Feature | Where in code | Status |
| --- | --- | --- |
| Firm portal per subdomain (`<slug>.kiensolutions.com`), firm branding, unknown/wrong-portal pages | `web/src/lib/tenant.ts`, `components/tenant/` | Merged |
| Dashboard with firm card and progress | `app/(portal)/page.tsx`, `progress/` | Merged |
| Questionnaire (no answers set N/A directly) | `questionnaire/`, `app/api/questionnaire.py` | Merged; direct reversible N/A (#55, #58) |
| 34-item numbered checklist, grouped in 6 sections, inline search beside "Open checklist" | `checklist/`, `data/checklist/aml_bd_v1.yaml` | Merged |
| Client marks N/A / undo directly; N/A sorts last, counts as done; progress over 32 collectable items | `app/api/intake.py` `/na` | Merged (#55, #58) |
| Upload center: drag-and-drop multi-file, confirm, per-file errors/retry, SHA-256 receipt, 100 MB limit, no item selection needed | `upload/`, `components/checklist/upload-dropzone.tsx` | Merged |
| Restricted items (AML-BD-017, AML-BD-025): "contact auditor", uploads rejected | catalog `restricted` flag | Merged |
| Messages page: document follow-ups (action-needed items) | `messages/page.tsx` | Merged |
| Neutral statuses: requested, checking, action needed (re-upload / more), with auditor, accepted for testing, not applicable, restricted | `app/checklist.ClientStatus` | Merged |

## Auditor workspace
| Feature | Where | Status |
| --- | --- | --- |
| Portfolio dashboard of assigned engagements | `auditor/page.tsx`, `components/auditor/portfolio.tsx` | Merged |
| Engagement workspace: documents per item, applicability + evidence decisions, internal notes, feedback, follow-ups | `auditor/engagements/[id]`, `app/api/manual_review.py`, `intake.py` | Merged |
| Full unrestricted access to own assigned clients' workspaces; can also set/undo N/A, sees who marked it (client or auditor) | `447e7f2` | Merged (#58) |
| Auditor upload center / organize unassigned documents | `auditor-upload-center.tsx` | Merged |
| Pipeline board (intake → document collection → auditor review → report drafting → awaiting signature → complete) | `auditor/pipeline`, `pipeline-board.tsx` | Merged |
| Tasks (priority, due date, complete) and upcoming tasks | `auditor_tasks`, `upcoming-tasks.tsx` | Merged |
| Activity feed and hash-chained audit log with chain verification | `auditor/audit-log`, `app/audit.py` | Merged |
| Create/switch firm workspaces; client invitations (create, resend, revoke) | `auditor/workspaces/new`, `client-invitations.tsx` | Merged |
| Settings: MFA enrollment, recovery codes | `auditor/settings` | Merged |
| Legacy report draft (DOCX/PDF) + hash sign-off | `app/reports/generator.py`, `/report/signoff` | Merged |
| **Editable reports**: per-engagement report, snapshot of firm/period/34 statuses, per-item findings, sanitized rich text, finalize with attestation + SHA-256, audited reopen, print view | `auditor/reports`, `app/api/reports.py`, migration `a114` | Merged (#56) |
| **Invoicing**: draft/sent/paid/void, partial payments, per-issuer numbering, filters incl. computed overdue, 6 currencies, print to PDF; shared within issuing auditor firm | `auditor/invoices`, `app/invoicing.py`, migration `a112` | Merged (#53, #54) |

## Shared / platform
| Feature | Status |
| --- | --- |
| Invite-only sign-in, magic link, password reset, invitations, setup | Backend merged; web flows temporarily removed |
| Auditor TOTP MFA + one-use recovery codes | Backend merged; web controls temporarily removed |
| **First sign-in walkthrough**: 3-step tour per role, shown only when `onboarding_state` is null; finish/skip/close/Escape all save to the account (works across devices) | Merged (#57 + #60) |
| Theme switch Light/Dark/System with sliding highlight and circular reveal, sits above the account block | Merged (#52) |
| Resizable/collapsible sidebar (200–360 px, saved), phone navigation sheet, command palette | Merged |
| shadcn-style compact dashboard layout + Impeccable refinements | Merged (#59) |
| Synthetic demo mode (`NEXT_PUBLIC_USE_MOCKS=true`), clearly labelled | Merged |
| Sentry error monitoring with strict scrubbing (optional, off when DSN blank) | Merged (code) — enabled state unverified |
| Background worker: receipt/integrity checks on uploads (no content inspection) | Merged |
| Egnyte storage connector | Built, **off** by default |

## Planned (not built)
Invoice follow-ups/reminders and Stripe (behind a flag), malware scan on uploads, general API rate limits, ops runbook, AWS move, SOC 2 groundwork, AI intake file sorting (auditor confirms), SAR pre-screen (zero model runs), FINRA chatbot. See `15-roadmap-build-order.md`.

## PR map (inferred from branch history; PR numbers from the working log)
| PR | Branch / commit | What |
| --- | --- | --- |
| #53 | `feat/auditor-invoicing` `57b52e5` | Invoice ledger |
| #54 | `7f18792` | Theme/sidebar polish, issuer-firm shared invoices |
| #55 | `2d912a2` | Reversible audited N/A |
| #56 | `dddcdd7` | Editable reports |
| #57 | `b8c1152` | Persistent role onboarding |
| #58 | `fix/na-client-auditor-access` `447e7f2` | Client N/A + auditor full access |
| #59 | `feat/shadcn-layout` | Compact layout + Impeccable |
| #60 | `fix/onboarding-once` `7cbe2be`, `02c480c` | Walkthrough once per account |
#50 is the separate design-branch exploration (`feat/apple-polish`, design.kiensolutions.com) — not approved.
