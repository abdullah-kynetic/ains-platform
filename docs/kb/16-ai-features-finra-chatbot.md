# AI features (built last)

Both features are **planned, not built**. `app/` must keep passing `tests/test_workflow_boundary.py` (no model SDKs in the workflow app); AI lives behind a separate authenticated adapter/module with its own data contract.

## A. Intake file sorting (F-11)
- Suggests which of the 34 checklist items an uploaded file belongs to; the **auditor confirms** before assignment.
- SAR/restricted detection routes files to the human-only lane **before** any model call; SAR is never sent to a model (F-12 pre-screen starts with zero model runs).
- Every suggestion cites document and page. Client sees only neutral document feedback.

## B. FINRA rules chatbot

### What it is
A rules helper inside the Kien client workspace (auditors can see what their clients asked). Answers questions about FINRA, SEC and BSA/AML rules with citations. **Not** legal advice. No access to client files or SAR material.

### Where it lives
Inside Kien — **not n8n**, not a separate product. Reasons: data stays in Kien's boundary (one place to secure and show in a SOC 2 audit), n8n sits on the shared OVH box we keep Kien away from, fewer moving parts, moves cleanly to AWS. The rule-refresh job is a small scheduled script in Kien.

### Exact stack
- **UI:** chat panel in the client workspace (Next.js/React, existing Kien components and colours), streamed answers, citation chips.
- **API:** new FastAPI chat endpoints (separate module/adapter, auth + firm scoping as usual).
- **Store:** existing PostgreSQL 16 + **pgvector** — rule passages with source, rule number, URL, effective date.
- **Embeddings:** cheap embedding model (default OpenAI `text-embedding-3-small`).
- **Search:** hybrid — vector similarity + Postgres full-text (so "Rule 3310" exact matches work), merged and re-ranked.
- **Answer model:** cheapest approved model that scores well on current benchmarks, behind a small **provider switch layer** (Anthropic / OpenAI) so models can change without code rewrites.
- **Ingestion:** Python script pulls public FINRA rules/notices, SEC rules (e.g. Reg S-P, 17a-8), FinCEN/BSA regs, plus Quentin's resources; chunks, embeds, re-runs on schedule/changes.
- **Guardrails:** answer only from retrieved passages; refuse if no source; every answer cites rule + link; "not legal advice" note; no client data in prompts; SAR terms trigger a refusal + "contact your auditor".
- **Logging + limits:** question, answer, sources, model, tokens, latency stored in Postgres; per-user rate limit; audit-chain event.
- **Testing:** pytest eval set of ~30 real client questions written by Quentin with expected answers/citations (pass/fail gate) + Playwright tests for the panel.

### Needs from Quentin
His FINRA/AML resources and the ~30 common client questions with good answers.

### Rough cost (estimate)
Embedding all rules: cents. Answers at low volume: a few dollars per month. No new database.

### Rollout
Own branch → preview → Quentin eval passes → Abdullah approves visuals → live behind a flag.

## Notes merged from the aborted "Kien FINRA Chatbot" run
No partially created Notion pages were found (searched 29 Oct 2026); the design above is the consolidated version from the 28–29 Oct conversation.
