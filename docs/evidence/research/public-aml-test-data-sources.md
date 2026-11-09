# Public AML test-data sources for Kien (research only, nothing built or scraped)

Date: 2026-11-07. "Verified" = I opened the page this session. "Inferred" = not checked.

## Short answer
No firm publishes its real AML evidence (onboarding files, training logs, ledgers) online, and we shouldn't want that anyway. What is public: the rules, the regulator templates, enforcement cases that describe AML failures, and fully synthetic transaction data. Use those as the knowledge base, and build our own fake client evidence from them.

## Ranked shortlist

| # | Source | What it is | Maps to checklist | Terms / scraping | Real-firm data? |
|---|---|---|---|---|---|
| 1 | FINRA AML Template for Small Firms (finra.org/compliance-tools/anti-money-laundering-template-small-firms) | Word doc: model AML policy text, rules, red flags (Reg Notice 19-18). Verified. | 001 policies, 020 risk assessment, 027 controls, 029 governance, 031 retention, 033 staffing | Page shows "© FINRA", no reuse licence stated (verified). Fine for internal testing; get Terms of Use read before redistributing or embedding verbatim. robots.txt does not block it (verified). One manual download, no crawling. | No (generic template) |
| 2 | FFIEC BSA/AML Examination Manual, independent testing section (bsaaml.ffiec.gov) | Federal examiner guidance: who tests, how often, scope, documentation, reporting. Verified. | 014, 021 independent testing, plus report structure | No copyright notice on page (verified). US-government work, likely public domain (inferred). Bank-focused, not broker-dealer, so use for method, not as FINRA rules. | No |
| 3 | FINRA Rule 3310, Regulatory Notices (e.g. 19-18 red flags, 21-03), annual exam findings reports (AML section) | Rules and what examiners actually find wrong. | All sections; good for a "what good looks like" rubric (leave rubric wording to Quentin) | finra.org content is copyright FINRA. Quote short passages, link the rest. Not blocked by robots.txt except specific pages. | No |
| 4 | FINRA enforcement actions (AWCs) on AML failures | Settled cases describing a firm's AML failures, including failure to independently test. Law-firm summaries exist (Orrick, Mondaq). | 021 independent testing, 003 training, 019 sanctions screening, 020 risk assessment, 013 and 026 government requests | **FINRA's Disciplinary Actions page is disallowed in robots.txt (verified), so no scraping.** Read a handful by hand, or use the law-firm summaries. SEC/FinCEN orders are another route (terms not checked). | **Yes, real named firms.** Public record, but use only as case inspiration. Never copy names into demo data. |
| 5 | IBM "AMLworld" synthetic transactions (github.com/IBM/AML-Data, also on Kaggle) | Synthetic bank/transaction CSVs, each tagged laundering or not. Verified. | 012 money movement, 010 ledger-style tests, 018 screening | Data licence is CDLA-Sharing-1.0 (verified); repo code is Apache-2.0. Sharing-1.0 requires sharing modified data under the same licence, so keep derived data out of anything we sell. Needs Abdullah/attorney OK. Kaggle download needs an account. | No, fully synthetic |
| 6 | Public firm AML policies / WSPs posted online | Some firms post AML policy or disclosure pages. I did not find a reliable set. | 001, 029 | Copyright of each firm. Don't copy. | **Yes**, skip unless needed |

Not recommended: anything labelled "leaked", "sample SAR" or SAR-like (hard rule 1), paid data vendors (cost), generic "AML policy template" sites (low quality, unclear licence).

## Suggested synthetic test set (to build after approval)
Build everything ourselves from sources 1 to 4, with invented firms ("Northgate Securities LLC" style) and invented people.

- 3 fake firms: clean, messy, and bad.
- Per firm, fake evidence for the 32 collectable items (skip 017 and 025, SAR-restricted): policy PDF from the FINRA template text, training log, signed rep letter, onboarding forms, 10 sample account files, a ledger extract, clearing-firm report, prior test report.
- Planted defects drawn from AWC patterns: no independent test for 2 years, training missing for staff, policy never updated, sanctions screening not run, wrong period, unreadable scan, missing pages.
- Use IBM AMLworld rows only for the money-movement and ledger items, if approved.
- A "known answers" sheet per firm so we can score what Kien's output catches. Quentin writes the real rubric.
- Total: roughly 100 to 150 small files.

## Needs Abdullah's decision
1. OK to use the FINRA template text as base material (one manual download)?
2. OK to use IBM data under CDLA-Sharing-1.0, or skip it?
3. Should I build the synthetic set next (agent time only, no spend)?

Note: the "free models only" AI trial rule applies if we later run AI over this set. Also, scraping isn't needed here; manual downloads of a few documents are enough.
