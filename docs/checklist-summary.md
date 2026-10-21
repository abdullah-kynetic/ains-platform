# Checklist implementation review

The source is [the complete 34-request reference](checklist/aml-ma-bd-request-list.md).
The versioned application catalog is `data/checklist/aml_bd_v1.yaml` (JSON-compatible YAML).
All source descriptions and table order are preserved. Plain-English titles and six sections
are implementation additions and remain pending Quinton's review.

| Section | Request numbers |
| --- | --- |
| Program and leadership | 1, 2, 20, 28, 29, 33 |
| Training and independent testing | 3, 14, 21 |
| Clients and due diligence | 7, 8, 9, 11, 16, 22, 24 |
| Transactions and payments | 4, 10, 12, 15, 23 |
| Screening and government requests | 13, 17, 18, 19, 25, 26, 34 |
| Systems, records, and controls | 5, 6, 27, 30, 31, 32 |

## Implemented

- Stable IDs `AML-BD-001` through `AML-BD-034`, exact descriptions, source headings,
  timing rules, conditional questions, and restricted flags.
- Requests 17 and 25 reject portal uploads. All other uploads still require restricted-content
  detection before any provider call; an unrestricted request is not permission to send SARs.
- Conditional questions for requests 4, 11, 12, 16, 22, and 24. Requests 12, 16, 22, and 24
  preserve the written-representation alternative when the answer is no.
- Request 9 is retained as an auditor-selected follow-up and initially hidden.
- Each new draft engagement stores a complete independent catalog snapshot. Updating the catalog
  does not change existing engagements. Initialization cannot overwrite an existing checklist.
- Auditor-only `POST /auditor/engagements` creates a new firm and assigned draft engagement.
  `GET /auditor/engagements` lists only the signed-in auditor's assigned engagements.
- Drafts are invisible to client APIs and accept no uploads. Hidden items accept no uploads.

## Still requiring implementation or auditor decisions

1. Quinton must confirm the source numbering and request 9 cross-reference, timing interpretations,
   conditional questions, and the six-section organization.
2. Accepted extensions are technical defaults, not requirements from the Word document. Minimum
   page count defaults to one. Request 2 requires a signature; detecting a signature does not
   validate signer authority or all required signers.
3. Natural-language timing rules are preserved in the snapshot. They are deliberately not wired
   to the existing simplistic any-date deterministic check. Coverage rules need individual tests.
4. Before activation, finish the audited publication action and representation collection flow:
   a negative answer must not eliminate a required written representation.
5. Implement auditor release of request 9 after selecting accounts/engagements. Keep all source
   requests even if Quinton later approves consolidated presentation of overlapping requests.
6. Existing tenant invitation, renewal engagement, and assignment changes need explicit access
   controls. The new endpoint creates a fresh tenant and never grants access to an existing one
   merely because the caller supplies its slug.

Catalog status is `pending_quinton_review`. Creating a draft does not approve or activate it.
