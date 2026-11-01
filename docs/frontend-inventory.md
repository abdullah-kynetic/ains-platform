# Frontend inventory and backend handoff

Branch `design/preview-cleanup`. Everything below runs on synthetic data. Screens that have no backend route yet call the typed mock layer in `web/src/lib/mock/*` through one interface, `web/src/lib/api/*` (import from `@/lib/api/index`). Each mocked function carries a `// TODO(backend)` comment with the route and shape it needs. Swapping in the real API means replacing the function bodies only; screens and types do not change.

Contracts: [`web/src/lib/api/types.ts`](../web/src/lib/api/types.ts) (camelCase). Seed data: `web/src/lib/mock/seed.ts`. Persisted in `localStorage` (`kien-mock-*` keys).

## Rules the UI already enforces (the server must too)

- A finding cannot be approved or issued without every field and at least one document + page citation. Editing an approved finding returns it to draft.
- Finding states: `draft → approved → issued → responded → closed`. Only `issued`, `responded` and `closed` findings ever reach the client portal.
- Sign-off order: all blockers clear → second reviewer approves → partner signs (typed name + attestation) → complete. Code never signs on its own; the report fingerprint (SHA-256 of section text) is recorded at signing and flagged if the report changes afterwards.
- Editing a workpaper's procedure or conclusion clears its review.
- N/A checklist items sort last and count as resolved.

**Conflict to decide:** `CLAUDE.md` says "never show audit findings in client UI". This build adds a client Findings page because it was asked for explicitly (management responses). It shows only formally issued findings, never drafts, causes, effects or citations. Confirm that is acceptable before wiring the backend, or hide the page behind a flag.

## Auditor routes

| Route | Screen | Main components |
| --- | --- | --- |
| `/auditor` | Today dashboard (needs attention, change indicators, deadlines, "Needs you today") | `auditor/today-view.tsx`, `auditor/portfolio.tsx` (existing) |
| `/auditor/clients` | Clients list | `auditor/clients.tsx` `ClientsList` |
| `/auditor/clients/[id]` | Client profile: firm type, contacts, engagement history | `ClientProfileView` |
| `/auditor/engagements` | Engagements list | `auditor/engagements-list.tsx` |
| `/auditor/engagements/[id]` | Overview tab | `auditor/engagement/overview.tsx`; shell and tabs in `engagement/shell.tsx` |
| `…/requests` | Requests (existing request-by-request review) | `auditor/manual-workspace.tsx` (existing) |
| `…/documents` | Documents with hashes and document-level feedback | `engagement/documents-activity.tsx` |
| `…/checklist` | 34-item checklist, Pass / Partial / Fail / Does not apply | `engagement/checklist-workpapers.tsx` |
| `…/workpapers` | Procedure, linked evidence, conclusion, preparer, reviewer | same file, `WorkpaperDialog` |
| `…/samples` | Population, sample size, items, results, exceptions | `engagement/samples.tsx` |
| `…/findings` | Structured findings, management response, status | `engagement/findings.tsx` |
| `…/report` | Report builder, preview, Word/PDF export, fingerprint | `engagement/report-signoff.tsx` `ReportTab` |
| `…/independence` | Independence / conflict record | `IndependenceTab` |
| `…/sign-off` | Second review, partner sign-off, mark complete | `SignoffTab` |
| `…/activity` | Activity log | `ActivityTab` |
| `/auditor/pipeline`, `/auditor/reports[/id]`, `/auditor/invoices[/new,/id,/id/edit]`, `/auditor/audit-log`, `/auditor/workspaces/new` | Existing screens reused from PRs #53–#60 (pipeline, report writing, invoicing, audit log) | unchanged |
| `/auditor/firm` → `/auditor/firm/team` | Team and roles | `auditor/firm/firm-tabs.tsx` `TeamTab` |
| `/auditor/firm/branding` | Firm name, tagline, logo | `BrandingTab` |
| `/auditor/firm/rubric` | Per-request scope and pass criteria | `RubricTab` |
| `/auditor/firm/templates` | Request-list templates (introducing, retail, self-clearing, custom) | `TemplatesTab` |
| `/auditor/notifications` | Notifications centre | `auditor/notifications.tsx` |
| `/auditor/settings` | My account, MFA recovery (existing) | existing |
| Cmd/Ctrl-K | Global search (clients, engagements, findings, requests, documents) | `shell/command-palette.tsx` |

Sidebar groups: **Workspace** (Today, Clients, Notifications), **Engagements** (Engagements, Audit pipeline, Reports, Invoices), **Firm** (Firm settings, Audit Log, My account).

## Client routes

| Route | Screen | Components |
| --- | --- | --- |
| first sign-in | Walkthrough, once ever (server-saved `onboarding_state`) | `auth/onboarding.tsx` (existing, copy updated) |
| `/` , `/upload`, `/checklist`, `/questionnaire` | Overview, document requests with upload, checklist with document feedback, questionnaire | existing |
| `/messages`, `/progress` | Feedback on documents, progress | existing |
| `/findings` | Issued findings needing a management response | `portal/results.tsx` `PortalFindings` |
| `/report` | Signed reports (Word / PDF) with fingerprint | `PortalReport` |
| `/invoices` | Invoices | `PortalInvoices` |

Sign-in, invitation, reset and MFA screens are unchanged.

## Mocked calls (`TODO(backend)`)

| Function (file) | Route needed | Shape |
| --- | --- | --- |
| `listClientProfiles`, `getClientProfile` (`clients.ts`) | `GET /auditor/clients`, `/{id}` | `ClientProfile` (firm type, CRD, clearing, contacts[], engagements[]) |
| `addContact` | `POST /auditor/clients/{id}/contacts` | `Contact` |
| `listEngagementSummaries`, `getEngagementSummary` | `GET /auditor/engagements`, `/{id}/summary` | `EngagementSummary` (firm, period, stage, due, lead, reviewer, partner) |
| `getChecklistTests`, `setConclusion` (`checklist.ts`) | `GET …/checklist-tests`, `PATCH …/{requestId}` | `ChecklistTest[]` with `conclusion: pass\|partial\|fail\|na\|null`; audit-log each change |
| `listDocuments` (`documents.ts`) | `GET …/documents` | `EngagementDocument` (sha256, pages, document-level `feedback` only) |
| `listWorkpapers`, `saveWorkpaper`, `reviewWorkpaper` (`workpapers.ts`) | `GET/PUT …/workpapers[/{requestId}]`, `POST …/review` | `Workpaper`; reviewer must differ from preparer |
| `listSamples`, `createSample`, `setSampleResult` (`samples.ts`) | `GET/POST …/samples`, `PATCH /auditor/samples/{set}/items/{item}` | `SampleSet` with `items[]`; exception note required |
| `listFindings`, `saveFinding`, `setFindingStatus`, `deleteDraftFinding` (`findings.ts`) | `GET/POST/PUT …/findings`, `POST /auditor/findings/{id}/status`, `DELETE` (drafts) | `Finding` (rule, condition, cause, effect, recommendation, severity, citations[], managementResponse, status) |
| `buildReport`, `saveReportSection`, `downloadWord` (`report.ts`) | `GET …/report-draft`, `PUT …/sections/{id}`, `GET …/report.docx` | `ReportDraft` assembled from non-draft findings; server renders Word/PDF from `templates/report` |
| `getIndependence`, `saveIndependence` (`signoff.ts`) | `GET/PUT …/independence` | `IndependenceRecord`; "yes" needs safeguards or the result is `not_independent` |
| `getSignoff`, `approveAsReviewer`, `partnerSign`, `completeEngagement` | `GET …/signoff`, `POST …/signoff/review`, `…/signoff/partner`, `POST …/complete` | `SignoffState`; server computes the fingerprint and enforces roles |
| `listActivity` (`log.ts`) | `GET …/activity` | `ActivityEntry[]` (server writes the trail; `logActivity` is display-only) |
| `listTeam`, `inviteMember`, `changeRole`, `removeMember` (`firm.ts`) | `GET/POST/PATCH/DELETE /auditor/firm/team` | `TeamMember`; block removing the last partner |
| `getBranding`, `saveBranding` | `GET/PUT /auditor/firm/branding` | `FirmBranding`; logo to object storage, not a data URL |
| `getRubric`, `saveRubricItem` | `GET/PUT /auditor/firm/rubric` | `RubricItem` (criteria empty until the partner approves) |
| `listTemplates`, `saveTemplate`, `deleteTemplate` | CRUD `/auditor/firm/request-templates` | `RequestTemplate` (kind, requestIds[]) |
| `listNotifications`, `markRead`, `markAllRead` (`notifications.ts`) | `GET /auditor/notifications`, `POST …/{id}/read`, `…/read-all` | `Notification` |
| `searchAll` (`search.ts`) | `GET /auditor/search?q=` | `SearchHit[]`, scoped to assigned engagements |
| `listPortalFindings`, `respondToFinding` (`portal.ts`) | `GET /client/findings`, `POST /client/findings/{id}/response` | `ClientPortalFinding`; only `issued` can be answered |
| `listPortalReports` | `GET /client/reports` | `ClientPortalReport`; `available` only when signed |
| `listPortalInvoices` | `GET /client/invoices` | `ClientPortalInvoice` |

Every new path needs a cross-tenant denial test (`firm_id` filter, assigned engagements only).

## Not mocked

Invoicing, report writing (existing `/auditor/reports`), pipeline, tasks, questionnaire, uploads, sign-in and onboarding keep their existing API clients (`invoice-api.ts`, `report-api.ts`, `workflow-api.ts`, `api.ts`).
