# Workflow API (Quentin's checklist flow)

Written 2026-11-10 by Lane 2. This is the contract Lane 1 wires against. Field names are
camelCase on the wire. `{eid}` is an engagement id, `{iid}` a checklist item id. Every route
resolves the engagement through the caller's scope (auditor: assigned only; client: own firm
only) and returns 404 for anything outside it. Every state change is written to the audit chain.
Clients never receive findings, internal notes, assessments or check results.

## Item states (derived, same words on both sides)

`not_started` · `submitted` · `needs_info` · `accepted` · `na` · `restricted`.
`accepted` means an auditor accepted the item's documents for testing. It is not an audit result.
A pending N/A request does not change the item state; it shows in `naRequest`.

## Engagement stages (derived from recorded facts)

`not_sent` → `checklist_sent` → `client_working` → `under_review` → `info_requested` →
`report_drafting` → `report_sent` → `confirmed` → `invoiced` → `paid`.
Returned as `stage` by the progress routes and as `workflowStage` (plus `checklistSentAt`) by
`GET /auditor/pipeline`. The existing six-value `stage` and its PATCH route are unchanged.

## Routes

| Who | Route | Body | Notes |
| --- | --- | --- | --- |
| auditor | `POST /auditor/engagements/{eid}/checklist/send` | none | Records dispatch once (409 if already sent or not initialized). Draft engagements become collecting. |
| both | `GET /auditor/engagements/{eid}/progress`, `GET /engagements/{eid}/progress` | | `{stage, checklistSentAt, clientSubmittedAt, reportConfirmedAt, counts, percentSubmitted, percentAccepted, items[]}`. Items carry `number` (original 1-34, never changes), `status`, `openIssues`, `naRequest`, `documents[{id, number, name}]`. N/A items sort last. |
| client | `POST /engagements/{eid}/items/{iid}/na-request` | `{reason}` (5-1000 chars) | Pending until an auditor decides. 409 if already pending, restricted or inactive. Can be asked again after a rejection. |
| auditor | `POST /auditor/engagements/{eid}/items/{iid}/na-request/decision` | `{decision: "accept"\|"reject", note?}` | Reject needs a note. Accept makes the item N/A (sorts last, number kept). Undo is the existing `POST /auditor/.../items/{iid}/na {not_applicable:false}`, which restores the previous state (back to pending). |
| client | `POST /engagements/{eid}/items/{iid}/na` with `not_applicable:true` | | Now 409: clients no longer declare N/A directly. |
| client | `POST` / `DELETE /engagements/{eid}/items/{iid}/documents/{docId}/link` | none | Link an uploaded document (any document of the engagement, uploaded or unassigned) to an item. Idempotent. |
| client | `POST /engagements/{eid}/items/{iid}/submit` | none | Needs a document and no open thread or pending N/A. |
| client | `POST /engagements/{eid}/submit` | none | Submits every ready item, returns `{submitted, notReady, stage}`. 409 if nothing is ready. |
| auditor | `POST /auditor/engagements/{eid}/items/{iid}/accept` | none | Needs a submitted item and no open thread. |
| auditor | `POST /auditor/engagements/{eid}/items/{iid}/issues` | `{kind: outdated\|wrong_year\|incorrect\|missing, documentId?, note}` | One atomic step: flag, open thread, first message, item to needs-info. `documentId` required unless `missing`; it must belong to the item. |
| both | `GET /auditor/engagements/{eid}/issues`, `GET /engagements/{eid}/issues` | | Threads: `{id, itemId, kind, status, document{id, number}, awaiting, messages[]}`. |
| both | `POST /engagements/{eid}/issues/{id}/replies`, `POST /auditor/engagements/{eid}/issues/{id}/replies` | `{body, documentId?}` | `documentId` is a re-upload (upload first, then reference it). A client reply moves the item back to with-auditor. |
| auditor | `POST /auditor/engagements/{eid}/issues/{id}/resolve` | `{note?}` | Only the auditor closes a thread. When the last thread closes the item leaves needs-info. |
| client | `GET /engagements/{eid}/report` | | Finalized report only (404 otherwise): `{engagementId, reportId, sections[{title, html}], finalizedAt, contentSha256, confirmed, confirmedAt}`. |
| client | `POST /engagements/{eid}/report/confirm` | `{contentSha256}` | Must equal the final hash (409 otherwise). Idempotent. Audit-logged. |

Document numbers: `1.<n>`, allocated per engagement at upload, never reused. They appear as
`number` on files in `GET /engagements/current`, in the workspace, in progress and in threads.

Invoices: `POST /auditor/invoices/{id}/sent` returns 409 for an engagement invoice until the
client has confirmed the report. The auditor marks paid with the existing `/paid` route. A
report the client confirmed cannot be reopened.

## Decisions to review (Lane 2 made these; Abdullah can overrule)

1. The client report view sends the human-authored sections only. The final report's sections can
   contain the findings text an auditor chose to publish, so the client sees findings only
   through a report a human finalized. Item-level findings, the status snapshot and internal
   fields are never sent.
2. An engagement invoice with no `engagementId` is not gated (manual invoices stay possible).
3. The checklist stays readable by the client before dispatch; uploads were already blocked for
   draft engagements. Lane 1 should use `checklistSentAt` to gate the screen.
