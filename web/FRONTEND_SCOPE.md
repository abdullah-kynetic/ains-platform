# Frontend scope from the October 21 meeting

The uploaded 34-request catalog is the source of truth. References to 40 requests in the meeting
were estimates. No source requests are deleted or renumbered by this frontend work.

| Meeting requirement | Frontend implementation |
| --- | --- |
| Fast overview and separate progress page (17:03–17:51) | Client overview with short next steps; `/progress` with section progress and neutral statuses |
| Per-client auditor overview (11:00–12:30) | All assigned engagements in `/auditor`; per-engagement dashboard and request counts |
| Documents and processing views (18:00–19:25) | Searchable 34-request inventory; queued/processing stages and elapsed-time examples |
| Every-document summary and cited assessment (19:44–20:59) | Auditor-only synthetic document summaries, sufficiency assessments, file/page quote excerpts |
| Auditor context and corrections (20:59–22:19) | Independent document decisions, explanation, category tags, review history, feedback export |
| Report after review (23:02–24:00) | Readiness screen with document, finding, N/A, restricted, and follow-up blockers; unsigned layout preview |
| Business-specific request list (25:16–27:43) | Existing firm questionnaire and full source checklist review retained |
| Theme options (15:29) | Light, dark, and system preference, remembered locally |

## Boundaries

This iteration changes frontend behavior and synthetic fixtures only. It does not provision
hosting, change authentication, ingest real documents, run AI, or train a model. The public
demo clearly identifies simulated state and resets workflow state on refresh. Client pages
never show internal findings, summaries, auditor explanations, or correction tags.

`AuditWorkspaceSource` in `src/lib/audit-preview.ts` defines the view's load/review boundary.
The synthetic adapter implements it; production mode retains the existing authenticated auditor
screen until a backend implementation is available. The new analytics views must not be enabled
against live data by silently substituting synthetic results.

## MCP integration later

MCP can provide a service connection if a server exposes the required tools and an authorized
authentication method (for example OAuth). It does not itself provide a model or turn a chat
subscription into hosted-app inference. A server offering document analysis could sit behind
the backend analysis adapter; a storage-only server cannot perform that analysis by itself.
Server URL, tool capabilities, and authentication method must be verified before selecting it.
No secret or model credential belongs in this frontend. Egnyte access must still respect the
application's guarded storage boundary. SAR-indicating files remain outside AI calls.

## Verification

Run web lint, typecheck, build, and Playwright tests. Browser tests cover client/auditor switching,
the complete request inventory, document review and correction history, report blockers, theme
selection, client isolation, and mobile overflow. Backend tests also verify demo catalog parity.
