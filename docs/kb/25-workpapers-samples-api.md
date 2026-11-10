# Workpaper and sample routes (L2-6b/6c)

Source: `app/api/testing.py`, `app/api/workpapers.py`; tests `tests/test_checklist_tests.py`,
`tests/test_workpapers_samples.py`. Shapes match `web/src/lib/api/types.ts`. Auditor-only; clients
get 403 and no client view carries any of these fields.

| Route | Notes |
| --- | --- |
| `GET /auditor/engagements/{id}/checklist-tests` | 34 rows, N/A last |
| `PATCH /auditor/engagements/{id}/checklist-tests/{requestId}` `{conclusion}` | `pass`, `partial`, `fail`, `na` or null |
| `GET /auditor/engagements/{id}/workpapers` | assigned auditor, or a reviewer or partner of the assignee's practice |
| `PUT /auditor/engagements/{id}/workpapers/{requestId}` | assigned auditor only; evidence ids must be documents of this engagement (422) |
| `POST /auditor/engagements/{id}/workpapers/{requestId}/review` | preparer cannot review (409); same reader rule as GET |
| `GET /auditor/engagements/{id}/samples` | assigned auditor |
| `POST /auditor/engagements/{id}/samples` | 201; size 1..500 and not above the population |
| `PATCH /auditor/samples/{setId}/items/{sampleItemId}` `{result, note?}` | returns the engagement's sets; 404 outside assigned engagements |

Editing a reviewed workpaper's procedure or conclusion clears the review. Every write is in the
client firm's audit chain.

## Decisions to review (Abdullah / Quentin)

- **Reviewer access.** An engagement has one assigned auditor, so an independent reviewer could not
  otherwise open it. A `reviewer` or `partner` in the same practice as the assignee can read
  workpapers and review them, and nothing else. Reviewer and partner assignment per engagement
  belongs to sign-off (L2-6f); this is the narrowest access that makes review possible now.
- **Sample items are numbered placeholders** (`ITEM-001`..). Picking items from a population file
  with a seed is not built, and the sampling method is free text; no method is suggested.
- **Conclusions are not coupled.** The checklist conclusion and the workpaper conclusion are
  separate human entries; neither is derived from the other or from documents.
