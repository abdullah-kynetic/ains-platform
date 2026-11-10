# Activity, notifications and search API (L2-6g)

Contract for `web/src/lib/api/log.ts`, `notifications.ts`, `search.ts`. Code: `app/api/feed.py`.
Migration `a127_notification_reads`. Auditor-only; clients have no route. Synthetic data only.

| Route | Returns |
|---|---|
| `GET /auditor/engagements/{id}/activity` | `ActivityEntry[]`, newest first, up to 100. Assigned auditor only (404 otherwise) |
| `GET /auditor/notifications` | `Notification[]`, newest first, up to 50, with `read` for the caller |
| `POST /auditor/notifications/{id}/read` | 204; 404 if the id is not one of the caller's current notifications |
| `POST /auditor/notifications/read-all` | 204 |
| `GET /auditor/search?q=` | `SearchHit[]`, up to 20; empty `q` returns `[]`; `q` max 100 chars |

## How each is built

- **Activity** reads the engagement's firm audit chain rows whose entity is the engagement or one
  of its items, documents, findings, response requests, workpapers, sample sets or finding drafts.
  The text is the action name as a sentence ("Workpaper saved."). Entered text is never shown;
  audit details already store lengths only. Client actors show as "Name (client)".
- **Notifications** are computed on each request from the caller's assigned engagements: deadline
  (due within 14 days or overdue, not complete), client upload (last 14 days), client response to a
  released request (last 14 days), reviewer approved, partner signed. Only read marks are stored
  (`notification_reads`, per user). `invoice`: own sent invoices past due and unpaid (added in L2-6h).
- **Search** matches firm names, engagement status, finding title or rule, checklist request id or
  title, and document name or number, only within assigned engagements. Wildcard characters are
  escaped. It never searches document contents.

## Decisions to review

- The existing `GET /auditor/activity` (latest 20 across engagements) is unchanged; the engagement
  screen should use the new per-engagement route instead of filtering that feed.
- A "Request" search hit links to the first assigned engagement's checklist, as the mock did.
- Notifications older than 14 days drop off and cannot be recalled; read marks for them remain.
- A reviewer or partner who is not the assigned auditor gets no notifications or search results
  for that engagement (they only reach workpapers and sign-off).
