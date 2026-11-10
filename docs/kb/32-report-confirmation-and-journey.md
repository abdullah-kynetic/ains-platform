# Signed-report confirmation and the end-to-end journey (L2-8)

Code: `app/api/signoff.py` (additions). No migration. Synthetic data only.

## The gap this closes

Two report paths existed. The old one (`/auditor/reports/*/finalize`, then the client's
`/engagements/{id}/report/confirm`) set the engagement's `report_confirmed_*` fields, which is
what lets an auditor issue an invoice. The new sign-off path (L2-6f) produced a signed report
the client could read but had no way to confirm, so those engagements could never be invoiced.

## What was added

- `POST /engagements/{id}/signed-report/confirm {fingerprint}` (client, own firm). 404 until the
  partner has signed and the engagement is complete; 409 if the fingerprint is not the signed
  one; recorded once (later calls change nothing); writes `report.confirmed` to the firm audit
  chain with the fingerprint; sets the same `report_confirmed_*` fields the invoice gate checks.
- `GET /engagements/{id}/signed-report` now also returns `confirmed` and `confirmedAt` (additive).
- `tests/test_end_to_end_flow.py`: one journey through conclusions, workpaper, finding, response
  request, client reply, independence, reviewer approval, partner signature, completion, client
  confirmation and invoice. It also proves the sign-off is blocked until the workpaper is reviewed
  by a second person and that findings text never reaches the client report.

## Regression coverage that already exists (re-run, not rebuilt)

Dispatch, reasoned N/A and ordering, document numbers and links, issue threads, report finalize
with hash and reopen, client confirmation gating the invoice, invites, password reset,
report-ready email, onboarding, subdomain tenancy: `tests/test_workflow_routes.py`,
`test_checklist_na.py`, `test_report_workflow.py`, `test_invoices.py`, `test_onboarding.py`,
`test_password_reset.py`, `test_report_ready_email.py`, `test_portal_tenancy.py`. They pass.

## Decisions to review

- Both report paths stay. Which one the pilot uses is Quentin's call; the old one is still the
  only path that sends the "report ready" email, and the new one sends none.
- The invoice gate treats either confirmation as enough.
- The old `report/signoff` route still moves an engagement to complete without a partner
  signature. Retiring it needs your decision.
- Live email delivery and the live subdomains are not verified here (Resend key and DNS are
  Lane C / Abdullah).
