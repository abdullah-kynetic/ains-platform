# Report draft routes (L2-6e)

Source: `app/api/report_draft.py`, `app/reports/draft.py`; tests `tests/test_report_draft.py`.
Shapes match `ReportDraft` and `ReportSection` in `web/src/lib/api/types.ts`. Auditor-only (assigned
auditor); no client route returns the draft, because it contains finding text.

| Route | Notes |
| --- | --- |
| `GET /auditor/engagements/{id}/report-draft` | assembled on the server, edits applied |
| `PUT /auditor/engagements/{id}/report-draft/sections/{sectionId}` `{body}` | replaces one section; returns the section; 409 while a final report exists |
| `GET /auditor/engagements/{id}/report-draft/docx` and `/pdf` | rendered from the same sections, marked "Draft. Not signed."; `no-store` |

Sections: `scope`, `approach`, `results`, one `finding-{id}` per finding that is not a draft, then
`limitations`. Counts come from the auditor's own checklist conclusions and recorded sample
results; finding sections copy the auditor's finding fields and the client's reply. Nothing is
concluded or written by a model. Edits and downloads are in the client firm's audit chain (edit
logs the text length only).

## Decisions to review (Abdullah / Quentin)

- **An edit is kept as typed.** If conclusions or findings change afterward, an edited section does
  not refresh; the auditor must edit it again. There is no reset-to-generated route yet.
- **The author name** in the scope text is the signed-in auditor's practice name, or "The audit
  firm" when they have no practice. It never says a firm passed.
- **Client reports and the fingerprint wait for sign-off (L2-6f).** The draft is not hashed or frozen
  here; the existing `/auditor/reports` finalize and `/engagements/{id}/report` client confirmation
  routes are unchanged and still work from their own content.
- **Word is a real `.docx`** (python-docx) and PDF uses reportlab; the web's HTML-as-.doc stand-in can
  be replaced by these routes.
