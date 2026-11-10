# Findings and client response requests (L2-6d)

Source: `app/api/findings.py`; tests `tests/test_findings.py` plus the registries in
`tests/security/`. Shapes match `web/src/lib/api/types.ts` (`Finding`, `ResponseRequest`).

**Boundary.** Findings are auditor-only. A client route returns only a `ResponseRequest`: the title
and text an auditor wrote when releasing an approved finding, plus the client's own reply. No
client response carries a finding id, severity, citation, rule, condition, cause, effect or
recommendation. `tests/security/test_client_fields.py` checks the client reads and writes.

| Route | Who | Notes |
| --- | --- | --- |
| `GET/POST /auditor/engagements/{id}/findings` | assigned auditor | create is 201 and always a draft |
| `PUT /auditor/engagements/{id}/findings/{findingRecordId}` | assigned auditor | editing an approved finding returns it to draft; issued findings 409 |
| `POST /auditor/findings/{findingRecordId}/status` `{status}` | assigned auditor | draft to approved (all fields and a citation of a real engagement document, 422 otherwise), approved to draft, issued or responded to closed; `issued` and `responded` cannot be set here |
| `DELETE /auditor/findings/{findingRecordId}` | assigned auditor | drafts only |
| `POST /auditor/findings/{findingRecordId}/response-request` `{title, requestText}` | assigned auditor | approved only; creates the client request and moves the finding to `issued`; once per finding |
| `GET /engagements/{id}/response-requests` | client of the firm | `ResponseRequest[]`, only released ones |
| `POST /engagements/{id}/response-requests/{responseRequestId}/response` `{text}` | client of the firm | open only (409 after); moves the finding to `responded` |

Only an auditor action approves a finding. Every write is in the client firm's audit chain; release
and reply log only the text length.

## Decisions to review (Abdullah / Quentin)

- **Paths differ from the web mock's TODO comments** (`/client/response-requests`,
  `/client/response-requests/{id}/response`, `POST /auditor/findings/{id}/response-request` is the
  same). Client routes live under `/engagements/{id}/...` to follow the route-inventory convention.
  Lane 1 should call the engagement-scoped paths with the id from `/engagements/current`.
- **One reply per request.** A client cannot edit or add a second reply; the request is then
  `responded`. Say if clients should be able to follow up.
- **No withdraw route** for a released request yet, and no way to re-release a closed finding.
- **The older item-based flow stays.** `POST .../items/{item}/response-request` and
  `GET /engagements/{id}/responses-requested` still work and are separate from this one.
- **Citation check** matches the cited name against a document's file name or document number.
  Page numbers are not checked against the document's page count (not stored).
- `FindingDraft` (the AI-era draft table and `PATCH /auditor/findings/{id}`) is untouched.
