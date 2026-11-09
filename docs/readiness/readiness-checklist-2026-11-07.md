# Readiness checklist before real client data

Source: the readiness checklist written on 2026-11-07 (Claude Docs doc "Kien: readiness checklist before real client data"). Copied here so it lives in the repo. Planning only. Nothing in this list has been changed or verified against live systems. Items marked *(inferred)* or *(unverified)* come from the docs, not from checking live systems.

Owners: **Claude** = a Claude build thread; **Abdullah**; **Quentin**; **Attorney** (Abdullah arranges).
**MUST** = blocks real client data. **NICE** = good to have, does not block.

## Short answers

- Yes, run synthetic tests. Yes, security work comes first. Real files should not enter until the Phase 1 to 4 MUST items are done.
- "Training": do not fine-tune on client data. Evaluate and improve prompts against Quentin-reviewed answers instead (Phase 6).
- Real data needs Abdullah's explicit written change to the mock-only rule (Phase 0).

## Phase 0. Decisions and rules (do first, cost nothing)

1. MUST, Abdullah: decide in writing that real client data may enter Kien, which clients, and from which date. Then update CLAUDE.md rule 2 and kb/12. Until then mock only.
2. MUST, Abdullah: confirm AI stays off for client data until Phase 6 is signed off. SAR items (AML-BD-017, 025) stay human-only forever.
3. MUST, Abdullah: name a security owner and a product owner of record (open question 9).
4. MUST, Abdullah: set retention and deletion rules and how much data loss is acceptable (open question 8).
5. NICE, Abdullah: monthly budget cap for hosting and AI (open question 6).

## Phase 1. Legal and consent

6. MUST, Attorney: engagement terms between Kien/Quentin's practice and each client covering confidentiality, who owns the files and reports, retention, and breach notice timing (Reg S-P service-provider duties, *unverified details*).
7. MUST, Attorney: written approval of Anthropic and OpenAI (today only verbal) and the retention terms to use. Needed before any client data touches a model.
8. MUST, Quentin and Abdullah: each client's written consent to being handled in Kien, and a separate consent line if their data is ever used for AI evaluation. Default: no.
9. MUST, Abdullah: cyber and E&O insurance in place (tracked in Notion hub, *status unverified*).
10. MUST, Attorney: decide whether Quentin's existing client files and past reports can be moved without fresh client permission (probably not).
11. NICE, Attorney: "not legal advice" wording for the chatbot.

## Phase 2. Infrastructure and security (build gaps)

12. MUST, Claude: restore real web sign-in (`AUTH_REMOVED` in `web/src/lib/api.ts`). Demo has none today.
13. MUST, Abdullah then Claude: stop using the shared OVH box for real data. Buy the dedicated VPS, handle credentials and DNS; Claude builds and migrates (preview first). The plan exists. Not started in production.
14. MUST, Claude: malware scan and quarantine on uploads.
15. MUST, Claude: general API rate limits and account lockout.
16. MUST, Claude and Abdullah: encrypted backups to a separate locked R2 bucket, with a scripted restore drill that actually passes. Abdullah holds the backup keys.
17. MUST, Claude: fix R2 storage compatibility in `app/storage/s3.py` (*unverified whether deployment config already covers it*).
18. MUST, Claude: secrets handling cleaned up (no hand-managed secrets, rotation steps written down).
19. MUST, Claude: confirm Sentry and logs hold no document content or SAR terms (scrubbing exists; check it in the deployed setup).
20. MUST, Claude and Abdullah: incident process (who is told, how fast) and a one-page runbook.
21. NICE, Claude: external checkpoint for the audit-log hash chain.
22. NICE, Abdullah: start SOC 2 groundwork (policies, access reviews). Never claim certification.

## Phase 3. Build gaps in the product

23. MUST, Claude: partner-firm separation. Today the tenant model separates client firms, not audit practices. One practice's data must never be visible to another. Only matters once a second audit practice (partner) is onboarded. For Quentin alone, it can wait, but then Quentin's practice must be the only practice on that instance.
24. MUST, Claude: a cross-tenant denial test on every API path, and checks that clients never see findings (only released Responses requested).
25. MUST, Claude: deletion and export of a client's data on request, matching the retention rule.
26. MUST, Quentin: fill the empty rubric fields for the 34 items (wording, applicability, allowed evidence). Software leaves them empty by design.
27. MUST, Quentin: confirm report template wording and what counts as sign-off (hash attestation vs real e-signature).
28. NICE, Claude: Stripe invoicing behind a flag, email reminders.

## Phase 4. Synthetic tests (run before any real file)

29. MUST, Abdullah: yes/no on the synthetic test set (3 fake firms, about 100 to 150 fake files, planted defects, known-answers sheet).
30. MUST, Claude: build it and run a full fake engagement end to end: invite, upload, N/A, review, report, sign, invoice.
31. MUST, Claude: run `uv run pytest -q`, `uv run ruff check .`, and the web unit and e2e tests on the final build. Not yet run for this plan.
32. MUST, Claude: security tests on the preview: tenant isolation, upload abuse (huge, empty, wrong type, fake extension), brute-force sign-in, SAR upload rejection.
33. MUST, Claude: restore a backup into a clean box and check a fake engagement comes back intact.
34. NICE, Abdullah: independent penetration test by an outside tester (a cost decision, yours).

## Phase 5. Dry run, then real data in small steps

35. MUST, Quentin: dry run on Quentin's own redacted/sanitized sample, approved by Quentin as non-identifying. No SAR.
36. MUST, Quentin and Abdullah: load one consenting client first, tell the client what is stored and where.
37. MUST, Abdullah: go-live check with Quentin (sign-in on, backups running, monitoring alert tested) before the second client.
38. NICE: past completed reports imported only after step 36 works and consent covers them.

## Phase 6. Models and evaluation (AI on client data)

39. MUST, Claude: keep the model adapter separate from `app/`, with logging of model, version, tokens and cost. `tests/test_workflow_boundary.py` keeps passing.
40. MUST: SAR detection runs before any model call, human-only lane.
41. MUST, Attorney: written approval for the chosen vendor, with zero or limited retention and no training on Kien's data in the vendor terms. OpenRouter is not approved for client data; synthetic only.
42. MUST, Quentin: about 30 real client questions with expected answers and citations, and review of AI output on synthetic files. This is the gold set.
43. MUST, Claude: eval harness that scores model output against Quentin's answers (pass/fail gates), run on synthetic data first. Free hosted models only for the first two weeks of the trial; no spend without Abdullah's approval.
44. MUST: AI only suggests; the auditor confirms. Every finding cites document and page. Quentin signs.
45. NICE, Claude: FINRA rules chatbot on public rules only, no client data.

## What fine-tuning on client data would need, and advice

Advice: do not do it now, and probably not for a long time. Reasons:

- It would need explicit written client consent for that use, which is different from consent to be audited.
- It needs vendor terms that allow fine-tuning on confidential data, with a clear answer on who holds the resulting model and whether the data is kept, plus a way to delete a client's data from a trained model (generally not possible).
- It collides with partner IP: partner data is not Kien's by default.
- Prompt and checklist-based evaluation against Quentin-approved answers gets most of the benefit with no data leaving, and can be redone as models change.
- Revisit only if evals show a clear gap, using synthetic or consented, de-identified data, with attorney sign-off first.

## Decisions only Abdullah can make

- Allow real data (Phase 0, item 1) and when.
- Buy the dedicated VPS and own credentials, DNS and backup keys.
- Yes/no on the synthetic test set and the IBM data licence.
- Budget cap and whether to pay for a penetration test.
- Whether Quentin's past client files are used, given the attorney's answer.
