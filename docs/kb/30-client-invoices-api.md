# Client invoices API (L2-6h)

Contract for `listPortalInvoices` in `web/src/lib/api/portal.ts` (`ClientPortalInvoice`).
Code: `app/api/client_invoices.py`. No migration. Synthetic data only.

`GET /engagements/{engagement_id}/invoices` (client only, own firm):
`{id, number, issued, due, amountCents, status}[]`, newest first.

- Shows `sent` and `paid` invoices of the client's firm that belong to this engagement or to no
  engagement. Drafts and voided invoices are never returned.
- `status` is `paid`, `overdue` (sent, past due, not fully paid) or `sent`.
- `number` is `KIEN-` plus the issuer's number, zero-padded to four digits, matching the mock.
- Line items, notes, payment history and internal events are not returned.
- Auditors get 403; a client of another firm gets 404.

Auditor side: `GET /auditor/notifications` now includes an `invoice` notification for each of the
caller's own sent invoices that is past due and unpaid (links to `/auditor/invoices/{id}`).

## Decisions to review

- The route lives under `/engagements/{id}/invoices`, not `/client/invoices` (client route rule).
  The client screen should pass its current engagement id.
- A firm-wide invoice (no engagement) shows under every engagement of that firm.
- `KIEN-` is a fixed prefix, not a per-practice setting.
- Invoices stay hidden until the auditor marks them sent (existing auditor flow).
