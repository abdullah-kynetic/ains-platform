# Kien project brief (source of truth)

Snapshot compiled 11 November 2026 (evening, America/Chicago) and folded into the repo on 12 November 2026. It is a snapshot, not a live dashboard. Where this brief and a file in the repo disagree on current scope, rules or process, this brief wins; fix the other file. If the live repo is clearly newer than this snapshot, trust the repo and update this file.

**No secrets here.** Never put passwords, API keys, tokens, key paths, server usernames or the contents of `/etc/kien/*.env` in the repo, Notion, logs or chat. Use environment variable names only.

Partner name is **Quentin** (never "Quinton").

## 1. Vision and scope

Kien Solutions is an AI-native auditing firm and platform. The long-term vision is to become the largest and best AI-native auditing firm across all auditing, not only FINRA AML testing. AML independent testing for broker-dealers is the first service and first proof case, with Quentin as the credentialed partner who signs reports. Each later audit type is added with a credentialed expert as partner.

The product is a full stack: client management, document collection, the 34-item AML checklist, auditor review, report writing, invoicing and payments. A FINRA-rules chatbot for client questions is planned later (AI for chat comes last). White-labeling to other auditors is under consideration.

Writing rules: company voice only; do not claim AWS's certifications as Kien's own. A future landing-page table "Kien (on AWS infrastructure) vs Egnyte" may include a "Kien SOC 2: in progress" row; that page is not being worked on yet.

Legal: on 8 November 2026 Quentin's attorney gave written sign-off for the model policy (see [model policy](kb/17-model-policy.md)). Cloud models, including via OpenRouter, are acceptable when provider terms, privacy controls and data permissions are in place. Suspicious Activity Report (SAR) material is confidential by law and must never be sent to any model, local or cloud.

## 2. People and how work gets done

- **Abdullah Ahmed**: founder, non-technical. Final say on deploys and on anything outside the merge rules in section 6.
- **Quentin**: partner and auditor of record. Signs reports. Runs an AML auditing practice for broker-dealer clients.
- **Slave Kien**: Abdullah's project assistant. Writes prompts and does work that needs its own access (server, DNS, live checks). It does not write Kien code.
- **Claude Code**: writes code, opens PRs and runs the independent security review in a separate fresh thread.
- **Codex / ChatGPT**: used when usage is available.

Hands-off rule: coordinators and builders work without coming back to Abdullah with questions. They make sensible choices, write them in the PR and report once at the end. Interrupt only for access, purchases, required approvals, or consequential changes (deploy, DNS that was not named, spending).

## 3. Friday 13 November 2026 investor demo

Goal: a full-system showcase, one complete audit end to end on the real, secure backend, in 5 to 15 minutes. Synthetic firm data only.

1. New client onboarding
2. Send the checklist
3. Reasoned N/A (items move to the bottom, numbered order); Quentin decides
4. Uploads and linking to checklist items
5. Auditor flags and requests; client Messages threads
6. Report, client confirmation and invoice
7. Firm-isolation proof and the audit log
8. If the AI slice is deployed and solid: auditor clicks "Run AI analysis", reviews drafts, Accept / Edit / Reject

If AI is not solid by Thursday night, the demo runs without it and AI is presented as what is next. Rehearse once, hand-timed, before Friday.

## 4. Current state (as of 11 November 2026, evening)

- **Repo:** `abdullah-kynetic/ains-platform`. Currently public; it must go private again after the demo (or sooner).
- **Live main:** commit `edbab14c1b2373e617c71daf4314fc92fb1db1c2` (includes emailed 6-digit sign-in codes, PR #136), image `kien-api:sha-edbab14c1b23`, migration `a129_email_sign_in_codes`. Rollback image: `kien-api:sha-664bd2539b62`; the server has a rollback script under `/opt/kien/deploy/`.
- **VPS:** `135.148.219.175` (Ubuntu, 2 vCPU, 3.7 GiB RAM, 2 GB swap). Hardened (key-only SSH, firewall for 22/80/443, fail2ban, Docker). App deployed and healthy: database, virus scanner, API, worker, web. Nightly backups on; a test restore passed. Settings of note (names only): `EMAIL_SIGN_IN_CODES=false` for now, `SESSION_COOKIE_SECURE=true`.
- **Old shared server `40.160.150.91`:** never touch. It hosts other Kynetic services.
- **Web:** Cloudflare Worker `ains-platform` (wildcard route `*.kiensolutions.com/*`). Firm portals are subdomains (for example `demo-securities.kiensolutions.com`); `auditor.kiensolutions.com` is the auditor host; `api.kiensolutions.com` is the shared backend and points at the VPS. `demo.kiensolutions.com` and the marketing site are unchanged.
- **Sign-in intent:** email and password on the first screen, then a 6-digit emailed code on a second screen, browser remembered about 30 days. Codes are built but switched off on the server for now.
- **Mac:** Abdullah's Mac (16 GB, Ollama with Qwen 3 14B installed) is used for local-model work.

## 5. Stage 3 AI analysis

The Stage 2 / Stage 3 gate wording that froze `audit_engine/**` and `ai_adapter/**` is **lifted for authorized Stage 3 work** (PR #137 and its follow-ups). Those folders are no longer frozen; changes still go through the PR, review and merge rules in section 6.

**PR #137** (head `573ec762858fb25ec9589ecd5495011dbec37da1` at snapshot): CI 12 of 12 green; independent security review passed all 10 items on the final pass (item 2 had two FAIL rounds; SAR scan gaps were fixed); verdict "safe to merge for the demo". Nothing was merged or deployed at snapshot time.

What it does: on a synthetic firm's engagement the auditor clicks "Run AI analysis". The AI reads up to 8 uploaded files (PDF, DOCX, TXT, CSV) plus linked checklist items and returns draft findings, document flags and suggested client requests, each citing document and page. The auditor can Accept, Edit or Reject. Accepting only creates an internal draft finding. Clients never see drafts or findings unless the auditor accepts and releases through the existing flow.

Safety in the PR:
- `AI_ANALYSIS_ENABLED` defaults to false. When off, the button is hidden and the endpoints return 404 (401/403 first for signed-out or wrong-role callers).
- SAR is blocked before any model call by restricted checklist IDs (AML-BD-017, AML-BD-025), tags, and a content scan (case, punctuation, look-alikes, run-together phrases, PDFs). Blocked files are skipped and the auditor is told why. Tradeoff: rare names such as "Caesar report" are also blocked.
- Firm and engagement ownership checks; firm A cannot reach firm B.
- Every AI call is audit-logged (firm, engagement, user, model, time) with no document text.
- Models: only exact `:free` OpenRouter IDs, price-checked to zero on every call, no paid fallback. Chosen 11 November: `google/gemma-4-26b-a4b-it:free` first, then `nvidia/nemotron-3-ultra-550b-a55b:free` only if the first fails upstream. Settings by name: `AI_ANALYSIS_ENABLED`, `AI_SERVICE_URL`, `AI_SERVICE_TOKEN`, `OPENROUTER_API_KEY` (the model key lives on the AI service only).

Known gaps at snapshot: no compose service or outbound rule for the AI service yet (so "Run" returns 503 on the live server); no OCR (scans and images are skipped); XLSX, DOC and XLS are skipped; runs are synchronous and a double-click starts two runs; live output quality is unmeasured; one Playwright spec (`web/e2e/ai-analysis-hidden.spec.ts`) was written but not run locally.

## 6. Standing rules (always on)

**Data and AI**
- Synthetic data only until the real-document conditions in section 7 are met.
- No SAR material to any model, ever. Clients never see findings or AI drafts.
- Only OpenRouter `:free` model IDs with a zero-price check. No paid fallback.
- AI calls are firm-scoped and audit-logged; no document text in logs. `AI_ANALYSIS_ENABLED=false` by default.

**Secrets, servers and docs**
- No secrets in the repo, Notion, logs or chat.
- Never touch `40.160.150.91`. Never change compose memory limits. Never overwrite the server's `deploy/` folder.
- restic backups: take the snapshot only; skip forget and prune (they hang) until fixed after the demo.
- Do not run `npm run deploy:production` as written; it can overwrite the `demo.kiensolutions.com` worker. Use the correct env flag.
- DNS changes only when named and approved.
- Kien docs live in GitHub and Notion only. Never Google Drive, Sheets or Docs, and never Twenty CRM, for Kien.
- Partner name is Quentin.

**Git:** merge commits only. No rebase, no squash, no force-push. Commit as `abdullah-kynetic <211030198+abdullah-kynetic@users.noreply.github.com>`.

**Merge rule (agents may merge without waiting for Abdullah).** A PR is merged to `main` with a merge commit once all five hold:
1. CI is fully green on the final commit.
2. An independent reviewer agent (fresh context, never the builder) has given PASS on every required security item and a one-line verdict "Safe to merge".
3. No secrets, keys or env file contents are in the code, logs or fixtures.
4. Tests and lint for that PR pass.
5. The PR does not deploy, change DNS, turn `AI_ANALYSIS_ENABLED` on in production, or SSH to a server.

If an item fails, fix it on the same branch, re-review only the failed items, and merge only when all five are true. If they cannot be made true, leave the PR open and tell Abdullah why. The builder and the security reviewer are never the same agent. For a docs-only PR the "safe to merge" review is a careful check that no secrets and no outdated or contradictory rules were introduced.

**Deploy rule (agents never deploy on their own).** Agents do not SSH to any server, do not deploy, and do not turn the AI switch on in production. When merging is done and a deploy is next, the agent stops and gives Abdullah a deploy brief and waits for his explicit "go":
- which PRs were merged and what is ready to deploy
- what changes on the server: compose service, outbound rule, env setting NAMES only, and whether the AI switch will be on
- the synthetic-firm smoke test to run after deploy
- a clear ask for him to say go

**Security review of AI code** is done by an independent Claude reviewer thread, then the merge rule above applies. This replaced the earlier "Slave Kien alone does the Stage 2 review" rule on 11 November 2026.

## 7. Ready for real documents (conditions are mandatory)

Abdullah wants the product able to run on Quentin's actual engagement files, not only synthetic ones. This is a higher bar than the investor walkthrough.

1. Quentin's OK, ideally written, before any real client file is used. Nobody but Quentin can give it.
2. SAR filings, narratives and related material are removed or blocked before any model call. The product blocks by checklist ID, tag and content scan; a person should still review the file set, and the auditor should see which files will be sent and which were skipped and why.
3. Prefer blanking client names and account numbers for a first real run.
4. The rubric in `audit_engine/rubric_draft.yaml` is a **DRAFT, needs Quentin's approval** (CIP AML-BD-009, CTR / large cash AML-BD-012, monitoring AML-BD-004, training AML-BD-003, independent testing AML-BD-021). Do not treat it as approved.
5. File types that work today: PDF (text), DOCX, TXT, CSV. Scans (no OCR), XLSX, DOC and XLS are skipped, and the auditor is told.
6. Live OpenRouter quality is unmeasured. Judge a first real run by comparing drafts with what Quentin would write, using a second engagement as a blind test when those materials are provided. Do not invent or request SAR material.
7. Cloud OpenRouter is allowed under the signed model policy with the existing guards. For a first pass on real files a local model on Abdullah's Mac (Qwen 3 14B in Ollama) keeps client text on the machine; local is the safer first real run. Real client files never go in the repo.
8. Synthetic firms under `data/synthetic/firms/` stay the default until the above are met. The broader rule also stands: all 45 readiness items, G1 and G2 and Abdullah's written authorization (see [readiness status](readiness/STATUS.md)).

"Done for Friday" means: the AI compose service and openrouter.ai-only outbound rule exist; after a deploy that Abdullah approves, `AI_ANALYSIS_ENABLED` is turned on only after a live synthetic-firm smoke test passes (Run, drafts, Accept / Edit / Reject; SAR block still works; the other firm's data is unreachable); a written, repeatable real-file path exists; and a real-engagement run happens only if Quentin has said OK and SAR-clean files are in hand. If not, the investor demo uses synthetic data and real-document work is the next step.

## 8. Product decisions outstanding or partly done

- **Bulk upload then sort** (Abdullah, 10 November): clients upload everything at once, then pick which checklist item(s) each file belongs to, or leave it unlinked. Demo minimum: a sorting list, dropdowns and an "unlinked" filter.
- **Checklist N/A:** reasoned N/A only (direct N/A removed, 11 November). Items move to the bottom in numbered order; the auditor (Quentin) decides.
- **Signing partner:** the assigned auditor may also be the signing partner (per-practice setting, default on for the demo practice, audit-logged); the second reviewer must differ.
- **Chatbot (later):** answers rule questions and questions about the client's own checklist, with isolation between clients and admin access across firms. Prefer a free approach. Not for Friday.
- **Permanent demo logins** on the synthetic firm (one client, one auditor) that never expire. Credentials live on the server, not in the repo.
- **Leftover firm** on the server cannot be deleted because an immutable audit-log trigger blocks it. Leave it; later make the seed ignore it.
- **The 7-step check script** from PR #134 was never committed. Commit it later.
- Still open: retention 2190-day placeholder (attorney), and the decisions in [open questions](kb/19-open-questions.md).

## 9. After the Friday demo

Do not do these during the investor slot:
- Turn off `ISOLATION_PROBE_ENABLED` and `INVITATION_PREVIEW_ENABLED`.
- Delete demo credential files (server and local copies).
- Change the server admin password.
- Fix the restic cleanup (forget/prune hang).
- Hide `/openapi.json`.
- Make the GitHub repo private.
- Make the seed ignore the leftover firm.
- Commit the 7-step check script.
- Turn email sign-in codes back on when ready to show the 30-day remembered browser.

## 10. Other open PRs (not the Friday AI path)

#103 (firm settings), #100 (single-env deploy), #73 (polish), #62 (design skills), #41 (landing page), #1 (older frontend). Do not merge these as part of the AI path unless a reviewer shows they are required and Abdullah agrees.

## 11. Where the rest lives

Plan files that lived only on Slave Kien's computer (local deploy guide, bulk-upload plan, older build plans) are historical. Their still-valid content is this brief and [BUILD-PLAN.md](BUILD-PLAN.md). A condensed copy of this brief is on the Notion hub: https://app.notion.com/p/416de1f1a268810bb096d6017b136d2a
