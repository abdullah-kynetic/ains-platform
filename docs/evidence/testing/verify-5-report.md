# VERIFY-5 report: PR #85 at 877c0b983e76339c39844ffcf29c201cc224232d

Environment: sandbox, Python 3.12.3, PostgreSQL 16.15 as `postgres`. No code fixed.

| Check | Result |
|---|---|
| ruff | PASS |
| PR test files (synthetic firms, uploads, workflow boundary) | PASS: 10 passed |
| Full suite excl. 4 PG files | PASS: 227 passed, 1 skipped |
| Five PG tests, non-root, PostgreSQL 16.15 | PASS: 5 passed |
| V4-1 fixed | PASS: quillfeather AML-BD-020 now has the one-paragraph marker; diffing every keyed defect file against the clean firm shows none identical to clean and no unkeyed differences |
| V4-2 fixed (marker test) | PASS: removing the thin-risk text, the signature line, the structuring rows, or altering the page marker each fail the marker test (and the determinism test); adding a marker to the clean firm fails the clean-firm test |
| Broadened PII test | PASS: patterns for email, SSN, EIN, phone, URL, street address, 9+ digit numbers, SAR phrase. Injecting a phone number and an email into a clean file fails the test. My own wider scan (8+ digits, SAR, IBM, 017/025 references) found nothing |
| Renamed firms | PASS: Zephyrine / Quillfeather / Brindlemoor "Example" names; test requires "Example" in each. Old names are gone from data; they remain in web/ mock seed files (pre-existing, outside this PR) |
| Byte-identical rebuild | PASS: fresh trees with PYTHONHASHSEED 3 and 999, 92 files, tree hash d02578a8a432ef2b, identical to committed; the test now builds into a temp dir instead of rewriting tracked files |
| 017/025 and answer keys | PASS: still absent; 32 items per firm; keys match files |

Remaining (Low): documents are now ~20-line templated text, better but still generic; fictional names cannot be checked against BrokerCheck offline; the ai_adapter `<document>` tag escaping note from VERIFY-4 is unchanged and outside this PR.
