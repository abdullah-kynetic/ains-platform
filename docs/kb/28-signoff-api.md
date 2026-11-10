# Independence and sign-off API (L2-6f)

Contract for `web/src/lib/api/signoff.ts` (types `IndependenceRecord`, `SignoffState`,
`ClientPortalReport`). Code: `app/api/signoff.py`. Migration `a126_engagement_signoffs`.
Synthetic data only. No model calls.

## Routes

| Route | Who | Notes |
|---|---|---|
| `GET /auditor/engagements/{id}/independence` | assigned auditor, or reviewer/partner of the assignee's practice | five fixed questions `q1`..`q5` owned by the server |
| `PUT /auditor/engagements/{id}/independence` | assigned auditor | conclusion is computed: all answered and no "yes" is `independent`; a "yes" with written safeguards is `safeguards_required`; otherwise `not_independent`; incomplete is `null`. 409 once the reviewer has approved |
| `GET /auditor/engagements/{id}/signoff` | as above | `SignoffState`; names are blank until someone acts |
| `GET /auditor/engagements/{id}/signoff/blockers` | as above | list of strings: open checklist conclusions, untested samples, unreviewed workpapers, draft findings (or findings with blockers), independence not cleared. New route, the screen used to compute this itself |
| `POST /auditor/engagements/{id}/signoff/review` `{note}` | reviewer or partner who is not the assigned auditor | 403 wrong role, 409 preparer, already approved, or blockers |
| `POST /auditor/engagements/{id}/signoff/partner` `{typedName}` | partner who is not the reviewer | needs reviewer approval and no blockers; typed name must equal the signer's name (case and spacing ignored, else 422). The server freezes all report sections (with edits) and stores their SHA-256 fingerprint |
| `POST /auditor/engagements/{id}/complete` | assigned auditor or a partner | needs the partner signature; sets the engagement to complete. No email is sent |
| `GET /engagements/{id}/signed-report` (client) | client of the firm | `ClientPortalReport`. `available` is false (no sections, no fingerprint) until signed and complete. Findings sections (`finding-*`) are removed |

After the partner signs, `PUT .../report-draft/sections/{id}` returns 409.

## Decisions to review

- No per-engagement reviewer assignment. Any reviewer or partner in the assignee's practice may
  approve, except the assigned auditor.
- The reviewer and the signing partner must be different people. A practice with one senior
  person cannot finish a file until a second reviewer or partner exists.
- The fingerprint covers the full signed report including findings sections; the client sees the
  fingerprint but only the non-findings sections, so they cannot recompute it.
- Independence is locked after reviewer approval; there is no "withdraw approval" route.
- Client route is `/engagements/{id}/signed-report` (single report per engagement), not
  `/client/reports`, to stay inside the client route rules.
- The legacy `report/signoff` and `/auditor/reports/*/finalize` flows are unchanged and not yet
  reconciled with this one.
