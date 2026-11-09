# VERIFY-4 report: PR #85 synthetic test set, head d7e0b4e (base main 87783af)

Environment: sandbox, Python 3.12.3, PostgreSQL 16.15 as user `postgres`. No code fixed.

| Check | Result |
|---|---|
| ruff | PASS |
| `pytest tests/test_synthetic_firms.py tests/test_synthetic_uploads.py tests/test_workflow_boundary.py` | PASS: 6 passed |
| Full suite excluding the four PG files | PASS: 223 passed, 1 skipped |
| Five PG tests, non-root, PostgreSQL 16.15 | PASS: 5 passed (the builder's failures were the root-user initdb issue) |
| Items 017/025 never produced | PASS: no file, answer-key entry or text reference in data/synthetic/firms; checklist YAML restricted set is exactly {017, 025}; each firm key has 32 items |
| Real-looking PII | PASS for emails, SSNs, phones, EINs, URLs, street addresses, 8+ digit numbers (all zero hits, own scan). Names are generic ("Jordan Example", "Riley Sample") |
| SAR content | PASS: no SAR/suspicious text in the firm files (only README mentions) |
| IBM / FINRA copying | PASS: no IBM/AMLworld/AMLSim strings except the README exclusion note; documents are one templated stub per item built from the checklist title, so nothing copied. Cannot compare with the FINRA template offline, so this rests on the generator code |
| Deterministic rebuild | PASS: rebuilt in two fresh worktrees with PYTHONHASHSEED 1 and 777; 92 files, byte-identical tree hash 98d2f07b2eb70e08, identical to the committed files |
| Prompt-injection sample inert | PASS: plain text line in lakeshore AML-BD-005; no markup, URL, code, encoded payload; no CSV cell starts with = + - @. Inert only as data; see note |
| Answer keys match planted defects | FAIL for one item (below); 13 of 14 other keyed defects verified by diffing files against the clean firm |

## Defects
V4-1 (Medium) harborview-capital AML-BD-020, key D-THIN-RISK-ASSESSMENT ("one paragraph, no customer or product factors") is not planted. The file is byte-identical to northgate's clean AML-BD-020 apart from the firm name. scripts/build_synthetic_firms.py `body()` has no branch for that defect. An evaluator would count a correct "no issue" as a miss. The key also lists 5 defects for harborview in index.json.
V4-2 (Medium, test gap) tests/test_synthetic_firms.py only asserts that defects exist for the two non-clean firms (`bool(defects) == ...`). Nothing checks that each keyed defect is present in its file, which is how V4-1 got through. The PII test covers only emails, SSNs and the phrase "suspicious activity report".
V4-3 (Low) Documents are 7-line stubs ("short invented sample covering: <title>"). Fine for the planted markers, poor for evaluating real extraction or sorting, and the clean/messy/bad contrast is mostly metadata.
V4-4 (Low, unverifiable offline) Firm names "Northgate Securities", "Harborview Capital Partners" and "Lakeshore Brokerage Group" look like plausible real names. Check them against BrokerCheck before sharing outside tests. "Meridian Trading Ltd" is marked "(invented)".
V4-5 (Low, not in this PR) ai_adapter/client.py wraps text as `<document>...</document>` without escaping, so a real injection containing `</document>` could break out. The sample here does not contain that.

Notes: scripts/evaluate_synthetic.py change is formatting only. The generator's `test_generator_is_deterministic` rewrites tracked files and passes only because output matches.
