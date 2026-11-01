# Feature inventory (as built)

> **Branch status (checked 29 Oct 2026):** `main` is at merge `12f6f70` (PR #52), Alembic head `a111`. PRs **#53–#60 are NOT merged into `main`**; they are a stack (#53 → #54 → #55 → #56 → #57 → #58 → #59 → #60) on top of `main` and are visible only on preview (preview.kiensolutions.com; #59 on layout.kiensolutions.com). Anything tagged **Preview (#NN)** below is not in a fresh `main` checkout. The shared OVH backend already runs the stacked code (`02c480c`, DB at `a115`), so the API serves these routes even though `main` does not contain them.

Status key: **Live** = merged to `main` and on live.kiensolutions.com · **Preview** = on an open, unmerged PR (not in `main`), deployed to preview.kiensolutions.com (and/or layout.kiensolutions.com), waiting for Abdullah's visual approval · **Planned** = not built.

Note: there is one shared backend on OVH. Codex deployed the stacked backend (latest `02c480c`) there, so backend behaviour for preview PRs is already running server-side; only the live *frontend* is held back. (inferred from Codex delivery logs)

## Client workspace
| Feature | Where in code | Status |
| --- | --- | --- |
| Firm portal per subdomain (`<slug>.kiensolutions.com`), firm branding, unknown/wrong-portal pages | `web/src/lib/tenant.ts`, `components/tenant/` | Live |
| Dashboard with firm card and progress | `app/(portal)/page.tsx`, `progress/` | Live |
| Questionnaire (no answers set N/A directly) | `questionnaire/`, `app/api/questionnaire.py` | Live; new N/A behaviour Preview (#55, #58) — `main` still has propose-N/A + auditor approval |
| 34-item numbered checklist, grouped in 6 sections, inline search beside "Open checklist" | `checklist/`, `data/checklist/aml_bd_v1.yaml` | Live |
| Client marks N/A / undo directly; N/A sorts last, counts as done; progress over 32 collectable items | `app/api/intake.py` `/na` | Preview (#55, #58) |
| Upload center: drag-and-drop multi-file, confirm, per-file errors/retry, SHA-256 receipt, 100 MB limit, no item selection needed | `upload/`, `components/checklist/upload-dropzone.tsx` | Live |
| Restricted items (AML-BD-017, AML-BD-025): "contact auditor", uploads rejected | catalog `restricted` flag | Live |
| Messages page: document follow-ups (action-needed items) | `messages/page.tsx` | Live |
| Neutral statuses: requested, checking, action needed (re-upload / more), with auditor, accepted for testing, not applicable, restricted | `app/checklist.ClientStatus` | Live |

## Auditor workspace
| Feature | Where | Status |
| --- | --- | --- |
| Portfolio dashboard of assigned engagements | `auditor/page.tsx`, `components/auditor/portfolio.tsx` | Live |
| Engagement workspace: documents per item, applicability + evidence decisions, internal notes, feedback, follow-ups | `auditor/engagements/[id]`, `app/api/manual_review.py`, `intake.py` | Live |
| Full unrestricted access to own assigned clients' workspaces; can also set/undo N/A, sees who marked it (client or auditor) | `447e7f2` | Preview (#58) |
| Auditor upload center / organize unassigned documents | `auditor-upload-center.tsx` | Live |
| Pipeline board (intake → document collection → auditor review → report drafting → awaiting signature → complete) | `auditor/pipeline`, `pipeline-board.tsx` | Live |
| Tasks (priority, due date, complete) and upcoming tasks | `auditor_tasks`, `upcoming-tasks.tsx` | Live |
| Activity feed and hash-chained audit log with chain verification | `auditor/audit-log`, `app/audit.py` | Live |
| Create/switch firm workspaces; client invitations (create, resend, revoke) | `auditor/workspaces/new`, `client-invitations.tsx` | Live |
| Settings: MFA enrollment, recovery codes | `auditor/settings` | Live |
| Legacy report draft (DOCX/PDF) + hash sign-off | `app/reports/generator.py`, `/report/signoff` | Live |
| **Editable reports**: per-engagement report, snapshot of firm/period/34 statuses, per-item findings, sanitized rich text, finalize with attestation + SHA-256, audited reopen, print view | `auditor/reports`, `app/api/reports.py`, migration `a114` | Preview (#56) |
| **Invoicing**: draft/sent/paid/void, partial payments, per-issuer numbering, filters incl. computed overdue, 6 currencies, print to PDF; shared within issuing auditor firm | `auditor/invoices`, `app/invoicing.py`, migration `a112` | Preview (#53, #54) |

## Shared / platform
| Feature | Status |
| --- | --- |
| Invite-only sign-in (password), magic link, password reset, invitation acceptance, account setup | Live |
| Auditor TOTP MFA + one-use recovery codes | Live |
| **First sign-in walkthrough**: 3-step tour per role, shown only when `onboarding_state` is null; finish/skip/close/Escape all save to the account (works across devices) | Preview (#57 + #60) |
| Theme switch Light/Dark/System with sliding highlight and circular reveal, sits above the account block | Live (#52) |
| Resizable/collapsible sidebar (200–360 px, saved), phone navigation sheet, command palette | Live |
| shadcn-style compact dashboard layout + Impeccable refinements | Preview on layout.kiensolutions.com (#59) |
| Synthetic demo mode (`NEXT_PUBLIC_USE_MOCKS=true`), clearly labelled | Live |
| Sentry error monitoring with strict scrubbing (optional, off when DSN blank) | Live (code) — enabled state unverified |
| Background worker: receipt/integrity checks on uploads (no content inspection) | Live |
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
