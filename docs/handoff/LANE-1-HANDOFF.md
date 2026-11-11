# Lane 1 handoff: wiring the web app to the real backend

Written Nov 10, 2026 (Pacific) for the Friday Nov 13 goal: one complete synthetic audit runs end
to end in the browser on the real backend in 5 to 15 minutes, with a firm-isolation proof and the
audit log. Update **Status** in every PR.

Read first: `CLAUDE.md`, `AGENTS.md`, `docs/BUILD-PLAN.md`, `docs/handoff/LANE-2-HANDOFF.md`,
`docs/frontend-inventory.md`, then the contracts in `docs/kb/23` to `docs/kb/33`.

## Status

| Step | What | PR | State |
| --- | --- | --- | --- |
| 0 | Two-practice isolation test + this route list | [#120](https://github.com/abdullah-kynetic/ains-platform/pull/120) | merged |
| 1 | New client onboarding | [#121](https://github.com/abdullah-kynetic/ains-platform/pull/121) | merged |
| 2 | Checklist sent to client | [#122](https://github.com/abdullah-kynetic/ains-platform/pull/122) | merged: engagement Overview "Client checklist" card (send, stage, counts); client stage banner on Overview and Checklist. Client: `web/src/lib/api/flow.ts` (all workflow routes, steps 2-5, with a synthetic mock for the mock build) |
| 3 | Client N/A with reason; Quentin approves or rejects | step-3 PR | done: client Checklist rebuilt on `/engagements/{id}/progress` (numbers, status, linked document numbers, N/A request with reason, rejection note, search); new auditor tab **Client checklist** (`…/client-checklist`) to approve or reject each N/A request |
| 4 | Client uploads (numbered `1.n`) and maps items to documents | | not started |
| 5 | Quentin flags problems and sends requests; client responds | | not started |
| 6 | Report, client confirmation, invoice | | not started |
| 7 | Firm-isolation proof screen and audit log view | | not started |
| 8 | Seeded synthetic demo script + `DEMO.md` | | not started |

Blockers: none yet.

Known inconsistency (not changed here, needs a decision): the questionnaire's own "No, mark N/A"
path (`POST /engagements/{id}/questionnaire/items/{iid}/na-review`) is older than the reasoned N/A
flow and is not part of the demo. The checklist screen shows such items as N/A.

## How the live browser tests run (added in step 1)

- `web/e2e-live/demo-journey-live.spec.ts` is the demo, one serial test per step, against the
  **real** FastAPI app (`scripts/e2e_backend.py`, throwaway SQLite, synthetic users). CI runs it in
  the new **Web journeys on the real backend** job (`npm run test:e2e:live`).
- Hosts: the web app needs a known firm host locally, so the auditor uses
  `http://kynetic.localhost:3100`; each new client firm uses `http://<slug>.localhost:3100`.
- `NEXT_PUBLIC_API_URL=http://{portal}:8000` (live config) makes each page call the API on its own
  host (`apiBase()` in `web/src/lib/api.ts`), so session cookies stay host-only and the API sees
  one firm. The placeholder is honoured only on `localhost` / `<label>.localhost`.
- The demo practice (`Synthetic Demo Practice`) has `e2e-quentin@example.test` (assigned auditor,
  partner) and `e2e-reviewer@example.test` (reviewer); sign-off needs both.
- `INVITATION_PREVIEW_ENABLED=true` in the test backend returns the one-time invitation link to the
  auditor instead of emailing it.

## Rules that apply to every route below

- Every route resolves its engagement through the caller's scope: an auditor sees only engagements
  assigned to them, a client only their own firm's. Anything outside scope is **404** (a few role
  failures are 403). The UI must treat 404 as "not yours", never retry with another id.
- `tests/test_two_practice_isolation.py` proves this for every route: two practices, two client
  firms, each side's real ids are sent to every route by the other side; all 74 id-bearing auditor
  routes return 404, no list, feed, search, team or audit-log read shows the other side's data, and
  no row on the other side changes. `tests/test_route_isolation.py` fails if a route is added
  without being listed in `tests/route_inventory.txt`.
- **Clients never see findings.** Client screens use only response requests, issue threads,
  progress, and the signed report (findings sections removed server-side).
- Session is a cookie; send `credentials: "include"`. Bodies and responses are camelCase except the
  older routes noted `snake_case`.
- Client routes start with `/engagements/{eid}`. Get `eid` from `GET /engagements/current`.
- Every state change writes the firm's audit chain on the server. The web never writes audit rows.

## Routes by demo step

`{eid}` engagement id, `{iid}` checklist item id, `A` auditor, `C` client.

### 1. New client onboarding (auditor: `/auditor/workspaces/new`, `/auditor/clients/[id]`; client: `/accept-invitation`, first sign-in)

| Method | Path | Role | Request → response | Screen |
| --- | --- | --- | --- | --- |
| POST | `/auditor/workspaces` | A | `{firm_name, review_period_start, review_period_end, due_date?}` (snake_case) → 201 `{id, firmId, firmName, slug, status, requestCount, clientAccessProvisioned}`; creates the client firm, engagement and checklist items | New workspace form |
| POST | `/auditor/engagements/{eid}/initialize` | A | none → `{requests: 34}`; only for older engagements with no items (409 otherwise) | not needed for new workspaces |
| GET | `/auditor/clients`, `/auditor/clients/{firm_id}` | A | → `ClientProfile[]` / `ClientProfile` | Clients list, profile |
| POST | `/auditor/clients/{firm_id}/contacts` | A | `Contact` → `Contact` | Client profile |
| GET/POST | `/auditor/engagements/{eid}/invitations` | A | `{email, name}` → `InvitationView {id, email, status, expiresAt, previewPath?}` | Client profile "Invite contact" |
| POST | `/auditor/invitations/{id}/resend`, `/revoke` | A | none → `InvitationView` | same |
| GET | `/auth/invitations/{token}` | public | → `{firmName, email, name, expiresAt}` | `/accept-invitation` |
| POST | `/auth/invitations/accept` | public | `{token, password}` (12+ chars) → session | `/accept-invitation` |
| GET/POST | `/auth/onboarding` | session | walkthrough state, once ever | first sign-in walkthrough |

`previewPath` is returned only when `invitation_preview_enabled` is on (demo/dev); live email is out
of scope this week, so the demo opens the invitation through `previewPath`.

### 2. Checklist sent to client (auditor engagement Overview; client Overview/Checklist)

| Method | Path | Role | Request → response | Screen |
| --- | --- | --- | --- | --- |
| POST | `/auditor/engagements/{eid}/checklist/send` | A | none → progress; 409 if sent or not initialized | Engagement Overview "Send checklist" |
| GET | `/auditor/engagements/{eid}/progress` | A | → `{stage, checklistSentAt, clientSubmittedAt, reportConfirmedAt, counts, percentSubmitted, percentAccepted, items[{id, number, requestId, title, status, openIssues, naRequest, documents[{id, number, name}]}]}` | Overview, Requests |
| GET | `/engagements/{eid}/progress` | C | same shape, client-safe | Client Overview, `/checklist`, `/progress` |
| GET | `/engagements/current` | C | → engagement with items and files (snake_case, files carry `number`) | Client shell |
| GET | `/auditor/pipeline` | A | rows with `workflowStage`, `checklistSentAt` | Pipeline |

Gate the client checklist on `checklistSentAt`.

### 3. N/A with a reason; Quentin approves or rejects

| Method | Path | Role | Request → response | Screen |
| --- | --- | --- | --- | --- |
| POST | `/engagements/{eid}/items/{iid}/na-request` | C | `{reason}` 5-1000 chars → item; 409 if pending/restricted | Client `/checklist` "Doesn't apply" |
| POST | `/auditor/engagements/{eid}/items/{iid}/na-request/decision` | A | `{decision: "accept"\|"reject", note?}` (reject needs note) → item | Auditor Requests tab |
| POST | `/auditor/engagements/{eid}/items/{iid}/na` | A | `{not_applicable: false}` → undo an accepted N/A | Auditor Requests tab |

`POST /engagements/{eid}/items/{iid}/na` by a client now returns **409**; do not call it. Accepted
N/A items sort last and keep their number.

### 4. Uploads numbered like 1.17, mapped to checklist items

| Method | Path | Role | Request → response | Screen |
| --- | --- | --- | --- | --- |
| POST | `/engagements/{eid}/documents` | C | multipart `file` → document with `number` (`1.n`, never reused) | Client `/upload` |
| POST | `/engagements/{eid}/items/{iid}/documents` | C | multipart `file` → document linked to the item | Client `/upload` per item |
| POST/DELETE | `/engagements/{eid}/items/{iid}/documents/{docId}/link` | C | none → item (idempotent) | Client `/checklist` "Map documents" |
| POST | `/engagements/{eid}/items/{iid}/submit` | C | none → item; needs a document, no open thread or pending N/A | Client `/checklist` |
| POST | `/engagements/{eid}/submit` | C | none → `{submitted, notReady, stage}` | Client "Submit all ready" |
| GET | `/engagements/{eid}/documents/{docId}/download` | C | → 60 s presigned link | Client files |
| GET | `/auditor/engagements/{eid}/workspace` | A | → items with documents, numbers, hashes | Auditor Requests, Documents |
| GET | `/auditor/engagements/{eid}/documents/{docId}/download` | A | → 60 s presigned link | Auditor Documents |
| POST | `/auditor/engagements/{eid}/items/{iid}/accept` | A | none → item; needs submitted item, no open thread | Auditor Requests |

### 5. Quentin flags problems and sends requests; client responds

Two kinds of request. Document flags (issue threads) are visible to the client. Findings are not;
only the response request the auditor writes is.

| Method | Path | Role | Request → response | Screen |
| --- | --- | --- | --- | --- |
| POST | `/auditor/engagements/{eid}/items/{iid}/issues` | A | `{kind: outdated\|wrong_year\|incorrect\|missing, documentId?, note}` → thread | Auditor Requests "Flag" |
| GET | `/auditor/engagements/{eid}/issues` | A | → `[{id, itemId, kind, status, document{id, number}, awaiting, messages[]}]` | Auditor Requests |
| POST | `/auditor/engagements/{eid}/issues/{id}/replies` | A | `{body, documentId?}` | same |
| POST | `/auditor/engagements/{eid}/issues/{id}/resolve` | A | `{note?}` | same |
| GET | `/engagements/{eid}/issues` | C | same thread shape | Client `/messages` |
| POST | `/engagements/{eid}/issues/{id}/replies` | C | `{body, documentId?}` (re-upload first, then reference) | Client `/messages` |
| GET/POST | `/auditor/engagements/{eid}/findings` | A | `Finding` → 201 draft | Auditor Findings tab |
| PUT | `/auditor/engagements/{eid}/findings/{findingRecordId}` | A | `Finding` | same |
| POST | `/auditor/findings/{findingRecordId}/status` | A | `{status: approved\|draft\|closed}`; approve needs every field and a citation of a real document | same |
| POST | `/auditor/findings/{findingRecordId}/response-request` | A | `{title, requestText}` → 201; finding becomes `issued` | same, "Request response" |
| GET | `/engagements/{eid}/response-requests` | C | → `[{id, title, requestText, status, response, respondedAt, releasedAt}]` | Client `/responses` |
| POST | `/engagements/{eid}/response-requests/{rid}/response` | C | `{text}` → request; once only | Client `/responses` |

Not `/client/response-requests` (the old mock comment). See `docs/kb/26-findings-api.md`.

### 6. Report, client confirmation, invoice (new sign-off path)

| Method | Path | Role | Request → response | Screen |
| --- | --- | --- | --- | --- |
| GET/PATCH | `/auditor/engagements/{eid}/checklist-tests[/{requestId}]` | A | `{conclusion: pass\|partial\|fail\|na}` | Checklist tab |
| GET/PUT | `/auditor/engagements/{eid}/workpapers[/{requestId}]`, POST `…/review` | A | `Workpaper`; reviewer ≠ preparer | Workpapers tab |
| GET | `/auditor/engagements/{eid}/report-draft` | A | `ReportDraft` | Report tab |
| PUT | `/auditor/engagements/{eid}/report-draft/sections/{sectionId}` | A | `{body}` → `{id, title, body}`; 409 after signing | Report tab |
| GET | `/auditor/engagements/{eid}/report-draft/docx`, `/pdf` | A | file | Report tab export |
| GET/PUT | `/auditor/engagements/{eid}/independence` | A | `{answers}` → `IndependenceRecord` | Independence tab |
| GET | `/auditor/engagements/{eid}/signoff`, `/signoff/blockers` | A | `SignoffState`, `string[]` | Sign-off tab |
| POST | `/auditor/engagements/{eid}/signoff/review` | reviewer/partner, not assignee | `{note}` | Sign-off tab |
| POST | `/auditor/engagements/{eid}/signoff/partner` | partner, not reviewer | `{typedName}` → fingerprint | Sign-off tab |
| POST | `/auditor/engagements/{eid}/complete` | A | none | Sign-off tab |
| GET | `/engagements/{eid}/signed-report` | C | `{available, sections, fingerprint, confirmed, confirmedAt}` (no findings) | Client `/report` |
| POST | `/engagements/{eid}/signed-report/confirm` | C | `{fingerprint}` → `{confirmed: true}`; unlocks invoicing | Client `/report` "Confirm" |
| POST | `/auditor/invoices` | A | `{firmId, engagementId, issueDate, dueDate, lineItems[{description, quantity, rateCents}]}` | `/auditor/invoices/new` |
| POST | `/auditor/invoices/{id}/sent`, `/paid`, `/void` | A | none; `sent` is 409 until the client confirmed | Invoice detail |
| GET | `/engagements/{eid}/invoices` | C | `[{id, number, issued, due, amountCents, status}]` | Client `/invoices` |

The sign-off needs **three different people** in one practice: the assigned auditor, a reviewer
(or second partner), and the signing partner. The demo seed must create all three.

### 7. Firm-isolation proof and audit log

| Method | Path | Role | Request → response | Screen |
| --- | --- | --- | --- | --- |
| GET | `/auditor/audit-log?firm_id=` | A (assigned to every engagement of that firm) | `{items[{id, firm_id, actor_id, action, entity_type, entity_id, created_at, sequence, previous_hash, row_hash}], …}` (snake_case); filters `action, entity_type, entity_id, actor_id, engagement_id, since, until, limit, offset` | `/auditor/audit-log` |
| GET | `/auditor/audit-log/verify-chain?firm_id=` | A | `{valid, checked, broken_at}` | `/auditor/audit-log` |
| GET | `/auditor/engagements/{eid}/activity` | A | `ActivityEntry[]` | Activity tab |

There is no backend "isolation proof" route, and none is needed: the proof screen should make
real calls with a foreign id and show the 404s, plus point to the test above. If a dedicated route
is added later it must not reveal whether a foreign id exists.

## Not in this week's scope

Secrets rotation doc, incident one-pager, audit-log checkpoint, invoice reminder emails, live
email, card payments, real data, AI items. `audit_engine/`, `ai_adapter/`, `deploy/` and compose
files are frozen until Abdullah's Stage 2 sign-off.

## Commands

- Backend: `uv sync --frozen && uv run ruff check . && uv run pytest -q`
- Web (`web/`): `npm ci && npm run lint && npm run typecheck && npm run test:unit && npm run test:e2e`
