# Commit plan: remaining backend slices (Phase 2)

Each line is one commit that stands on its own: it builds, passes its own tests and does one thing. Do not add empty, filler or whitespace commits. If a step turns out to be too big, split it; if two steps cannot pass separately, merge them. Real merge commits only, no rebase, no squash, no force-push.

Already merged or open: Phase 1 cleanup (#74, #75) and the clients, contacts and engagement summaries slice (#76).

Commit message format: `<slice>: <step>` (for example `findings: add the model and migration`).


## Slice 1: Checklist test results (Pass/Partial/Fail/Does not apply; N/A counts as resolved)

1. `checklist_test`: Add the model and an additive Alembic migration
2. `checklist_test`: Add request and response schemas matching `web/src/lib/api/types.ts`
3. `checklist_test`: Add the service logic and its rules (state transitions, validation)
4. `checklist_test`: Add the API endpoints behind auth
5. `checklist_test`: Add `firm_id` and engagement-assignment scoping plus an audit-log entry
6. `checklist_test`: Add tests, including a cross-tenant denial test
7. `checklist_test`: Replace the web mock call with the real API call and update `docs/frontend-inventory.md`

## Slice 2: Documents listing with hashes and document-level feedback

8. `document_listing`: Add the model and an additive Alembic migration
9. `document_listing`: Add request and response schemas matching `web/src/lib/api/types.ts`
10. `document_listing`: Add the service logic and its rules (state transitions, validation)
11. `document_listing`: Add the API endpoints behind auth
12. `document_listing`: Add `firm_id` and engagement-assignment scoping plus an audit-log entry
13. `document_listing`: Add tests, including a cross-tenant denial test
14. `document_listing`: Replace the web mock call with the real API call and update `docs/frontend-inventory.md`

## Slice 3: Workpapers (procedure, evidence, conclusion, preparer, reviewer)

15. `workpaper`: Add the model and an additive Alembic migration
16. `workpaper`: Add request and response schemas matching `web/src/lib/api/types.ts`
17. `workpaper`: Add the service logic and its rules (state transitions, validation)
18. `workpaper`: Add the API endpoints behind auth
19. `workpaper`: Add `firm_id` and engagement-assignment scoping plus an audit-log entry
20. `workpaper`: Add tests, including a cross-tenant denial test
21. `workpaper`: Replace the web mock call with the real API call and update `docs/frontend-inventory.md`

## Slice 4: Samples (population, sample size, items, results, exceptions)

22. `sample`: Add the model and an additive Alembic migration
23. `sample`: Add request and response schemas matching `web/src/lib/api/types.ts`
24. `sample`: Add the service logic and its rules (state transitions, validation)
25. `sample`: Add the API endpoints behind auth
26. `sample`: Add `firm_id` and engagement-assignment scoping plus an audit-log entry
27. `sample`: Add tests, including a cross-tenant denial test
28. `sample`: Replace the web mock call with the real API call and update `docs/frontend-inventory.md`

## Slice 5: Findings (structured fields, citations, status transitions)

29. `finding`: Add the model and an additive Alembic migration
30. `finding`: Add request and response schemas matching `web/src/lib/api/types.ts`
31. `finding`: Add the service logic and its rules (state transitions, validation)
32. `finding`: Add the API endpoints behind auth
33. `finding`: Add `firm_id` and engagement-assignment scoping plus an audit-log entry
34. `finding`: Add tests, including a cross-tenant denial test
35. `finding`: Replace the web mock call with the real API call and update `docs/frontend-inventory.md`

## Slice 6: Response-request release (auditor-written title and request text only)

36. `response_request`: Add the model and an additive Alembic migration
37. `response_request`: Add request and response schemas matching `web/src/lib/api/types.ts`
38. `response_request`: Add the service logic and its rules (state transitions, validation)
39. `response_request`: Add the API endpoints behind auth
40. `response_request`: Add `firm_id` and engagement-assignment scoping plus an audit-log entry
41. `response_request`: Add tests, including a cross-tenant denial test
42. `response_request`: Replace the web mock call with the real API call and update `docs/frontend-inventory.md`

## Slice 7: Report assembly from approved findings and tested results

43. `report_assembly`: Add the model and an additive Alembic migration
44. `report_assembly`: Add request and response schemas matching `web/src/lib/api/types.ts`
45. `report_assembly`: Add the service logic and its rules (state transitions, validation)
46. `report_assembly`: Add the API endpoints behind auth
47. `report_assembly`: Add `firm_id` and engagement-assignment scoping plus an audit-log entry
48. `report_assembly`: Add tests, including a cross-tenant denial test
49. `report_assembly`: Replace the web mock call with the real API call and update `docs/frontend-inventory.md`

## Slice 8: Report export (Word and PDF from templates/report) and fingerprint

50. `report_export`: Add the model and an additive Alembic migration
51. `report_export`: Add request and response schemas matching `web/src/lib/api/types.ts`
52. `report_export`: Add the service logic and its rules (state transitions, validation)
53. `report_export`: Add the API endpoints behind auth
54. `report_export`: Add `firm_id` and engagement-assignment scoping plus an audit-log entry
55. `report_export`: Add tests, including a cross-tenant denial test
56. `report_export`: Replace the web mock call with the real API call and update `docs/frontend-inventory.md`

## Slice 9: Independence record

57. `independence`: Add the model and an additive Alembic migration
58. `independence`: Add request and response schemas matching `web/src/lib/api/types.ts`
59. `independence`: Add the service logic and its rules (state transitions, validation)
60. `independence`: Add the API endpoints behind auth
61. `independence`: Add `firm_id` and engagement-assignment scoping plus an audit-log entry
62. `independence`: Add tests, including a cross-tenant denial test
63. `independence`: Replace the web mock call with the real API call and update `docs/frontend-inventory.md`

## Slice 10: Second-reviewer approval

64. `second_review`: Add the model and an additive Alembic migration
65. `second_review`: Add request and response schemas matching `web/src/lib/api/types.ts`
66. `second_review`: Add the service logic and its rules (state transitions, validation)
67. `second_review`: Add the API endpoints behind auth
68. `second_review`: Add `firm_id` and engagement-assignment scoping plus an audit-log entry
69. `second_review`: Add tests, including a cross-tenant denial test
70. `second_review`: Replace the web mock call with the real API call and update `docs/frontend-inventory.md`

## Slice 11: Partner sign-off (server-computed fingerprint) and mark complete

71. `partner_signoff`: Add the model and an additive Alembic migration
72. `partner_signoff`: Add request and response schemas matching `web/src/lib/api/types.ts`
73. `partner_signoff`: Add the service logic and its rules (state transitions, validation)
74. `partner_signoff`: Add the API endpoints behind auth
75. `partner_signoff`: Add `firm_id` and engagement-assignment scoping plus an audit-log entry
76. `partner_signoff`: Add tests, including a cross-tenant denial test
77. `partner_signoff`: Replace the web mock call with the real API call and update `docs/frontend-inventory.md`

## Slice 12: Firm team and roles

78. `team`: Add the model and an additive Alembic migration
79. `team`: Add request and response schemas matching `web/src/lib/api/types.ts`
80. `team`: Add the service logic and its rules (state transitions, validation)
81. `team`: Add the API endpoints behind auth
82. `team`: Add `firm_id` and engagement-assignment scoping plus an audit-log entry
83. `team`: Add tests, including a cross-tenant denial test
84. `team`: Replace the web mock call with the real API call and update `docs/frontend-inventory.md`

## Slice 13: Firm branding (logo in object storage)

85. `branding`: Add the model and an additive Alembic migration
86. `branding`: Add request and response schemas matching `web/src/lib/api/types.ts`
87. `branding`: Add the service logic and its rules (state transitions, validation)
88. `branding`: Add the API endpoints behind auth
89. `branding`: Add `firm_id` and engagement-assignment scoping plus an audit-log entry
90. `branding`: Add tests, including a cross-tenant denial test
91. `branding`: Replace the web mock call with the real API call and update `docs/frontend-inventory.md`

## Slice 14: Checklist rubric (criteria stay empty until Quentin approves)

92. `rubric`: Add the model and an additive Alembic migration
93. `rubric`: Add request and response schemas matching `web/src/lib/api/types.ts`
94. `rubric`: Add the service logic and its rules (state transitions, validation)
95. `rubric`: Add the API endpoints behind auth
96. `rubric`: Add `firm_id` and engagement-assignment scoping plus an audit-log entry
97. `rubric`: Add tests, including a cross-tenant denial test
98. `rubric`: Replace the web mock call with the real API call and update `docs/frontend-inventory.md`

## Slice 15: Request-list templates (introducing, retail, self-clearing, custom)

99. `templates`: Add the model and an additive Alembic migration
100. `templates`: Add request and response schemas matching `web/src/lib/api/types.ts`
101. `templates`: Add the service logic and its rules (state transitions, validation)
102. `templates`: Add the API endpoints behind auth
103. `templates`: Add `firm_id` and engagement-assignment scoping plus an audit-log entry
104. `templates`: Add tests, including a cross-tenant denial test
105. `templates`: Replace the web mock call with the real API call and update `docs/frontend-inventory.md`

## Slice 16: Notifications

106. `notifications`: Add the model and an additive Alembic migration
107. `notifications`: Add request and response schemas matching `web/src/lib/api/types.ts`
108. `notifications`: Add the service logic and its rules (state transitions, validation)
109. `notifications`: Add the API endpoints behind auth
110. `notifications`: Add `firm_id` and engagement-assignment scoping plus an audit-log entry
111. `notifications`: Add tests, including a cross-tenant denial test
112. `notifications`: Replace the web mock call with the real API call and update `docs/frontend-inventory.md`

## Slice 17: Global search scoped to assigned engagements

113. `search`: Add the model and an additive Alembic migration
114. `search`: Add request and response schemas matching `web/src/lib/api/types.ts`
115. `search`: Add the service logic and its rules (state transitions, validation)
116. `search`: Add the API endpoints behind auth
117. `search`: Add `firm_id` and engagement-assignment scoping plus an audit-log entry
118. `search`: Add tests, including a cross-tenant denial test
119. `search`: Replace the web mock call with the real API call and update `docs/frontend-inventory.md`

## Slice 18: Client portal: response requests

120. `portal_responses`: Add the model and an additive Alembic migration
121. `portal_responses`: Add request and response schemas matching `web/src/lib/api/types.ts`
122. `portal_responses`: Add the service logic and its rules (state transitions, validation)
123. `portal_responses`: Add the API endpoints behind auth
124. `portal_responses`: Add `firm_id` and engagement-assignment scoping plus an audit-log entry
125. `portal_responses`: Add tests, including a cross-tenant denial test
126. `portal_responses`: Replace the web mock call with the real API call and update `docs/frontend-inventory.md`

## Slice 19: Client portal: signed reports

127. `portal_reports`: Add the model and an additive Alembic migration
128. `portal_reports`: Add request and response schemas matching `web/src/lib/api/types.ts`
129. `portal_reports`: Add the service logic and its rules (state transitions, validation)
130. `portal_reports`: Add the API endpoints behind auth
131. `portal_reports`: Add `firm_id` and engagement-assignment scoping plus an audit-log entry
132. `portal_reports`: Add tests, including a cross-tenant denial test
133. `portal_reports`: Replace the web mock call with the real API call and update `docs/frontend-inventory.md`

## Slice 20: Client portal: invoices

134. `portal_invoices`: Add the model and an additive Alembic migration
135. `portal_invoices`: Add request and response schemas matching `web/src/lib/api/types.ts`
136. `portal_invoices`: Add the service logic and its rules (state transitions, validation)
137. `portal_invoices`: Add the API endpoints behind auth
138. `portal_invoices`: Add `firm_id` and engagement-assignment scoping plus an audit-log entry
139. `portal_invoices`: Add tests, including a cross-tenant denial test
140. `portal_invoices`: Replace the web mock call with the real API call and update `docs/frontend-inventory.md`

## Wrap-up for Phase 2

141. Docs: update `docs/DATABASE.md` for the new tables
142. Docs: update `docs/kb/05-data-model.md`
143. Docs: update `docs/kb/07-api-reference.md`
144. Docs: update `docs/SECURITY.md` for sign-off and response-request rules
145. Docs: update `docs/TESTING.md` with the new test layers
146. Test: add an end-to-end journey for finding to response request to client reply
147. Test: add an end-to-end journey for report to second review to partner sign-off
148. Test: add an axe pass over every new real-API screen
149. Chore: remove the mock functions that now have real routes (keep `USE_MOCKS` fallbacks only)
150. Chore: refresh the screenshots in `docs/evidence`

Total: 150 commits for Phase 2. Phases 3 to 6 (restore auth, security hardening, Stripe, AWS preparation) are planned separately in `docs/codex-handoff.md`.
