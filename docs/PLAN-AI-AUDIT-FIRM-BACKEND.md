# Plan: Kien as the backend of an AI-native auditing firm

Status: PLAN ONLY (2026-11-21). No code, deploy, DNS or server change. It authorizes nothing. [PROJECT-BRIEF.md](PROJECT-BRIEF.md) and [RULES.md](RULES.md) win over this file. Items marked **[inferred]** are my reading of the repo, not verified facts. Costs are rough estimates, not quotes. Nothing here claims a deployed state or an AWS certification.

## 1. Short version (plain English)

- **Today Kien is a good AML-testing workflow.** One engagement runs end to end on a real backend: intake, checklist, uploads, auditor review, findings, report, client confirmation, invoice, audit log. A first AI analysis slice is merged but switched off.
- **To be the backend of a whole firm, five things are missing:** (1) a way to run many audit types, not just the 34-item AML checklist; (2) firm operations (staffing, scheduling, time, client records, renewals); (3) AI that is staged, measured and always human-approved; (4) a real quality and sign-off system (independence, second review, retention); (5) SOC 2 groundwork.
- **Recommended order:** finish AML properly (real documents under Quentin's OK, measured AI) before adding firm-ops, and add a second audit type only after AML repeats reliably. This matches the vision's own stage order ([VISION.md](VISION.md)).
- **Cost stays near today's level** (about $0 to $60 a month of new spend through the first three phases) if we stay on the existing VPS, Cloudflare free tiers, R2 free tier, Resend free tier and `:free` models. The first real costs are a bigger VPS and paid models, and both are your decisions.
- **Nine decisions for you are in section 9.** The most important: approve the plan order, approve the "audit type" design spike, and decide when paid AI models may be used.

## 1a. More than audit software: five layers (Abdullah, 2026-11-20)

Abdullah wants Kien to be more than auditing software. Kien is the system the firm runs on, plus a product clients use all year. The five layers below are the frame for the rest of this plan:

| Layer | What it means | Today | Where in this plan |
|---|---|---|---|
| 1. Firm operating system | Sales pipeline, proposals and engagement letters, scheduling and staffing, time, billing and payments, auditor credential tracking | Invoices, tasks, assignment, client profiles | Phase 2 |
| 2. Audit delivery | Engagements for many audit types | AML end to end | Phases 1 and 3 |
| 3. AI workforce | Staged AI agents doing prep at each step; humans approve and sign | AI analysis slice (off) | Section 4, Phase 4 |
| 4. Year-round client compliance hub | AML program health, policy templates, training tracking, regulatory change alerts, FINRA chatbot; subscription revenue between annual tests | Not built | New Phase 4b (below) |
| 5. Platform for other firms | Partner firms under their own brand; credentialed experts per specialty; each firm's data stays its own | Practice layer only | Phase 5 |

**Phase 4b, year-round client hub [inferred scope; needs Abdullah's pick and Quentin's input]:** client-side compliance calendar and reminders, policy and procedure template library (Quentin-approved), training completion log, regulatory change feed from public sources (FINRA, SEC, FinCEN), and the chatbot. No client document goes to a model without the same SAR screen and human gates. Independence check needed: an auditor that also sells compliance tools to the same client may face independence limits under the audit rules; Quentin and the attorney must confirm before this is sold to audit clients **[inferred risk]**.

**DECIDED (Abdullah, 2026-11-20): the firm operating system is the next layer after AML is solid.** The other layers follow later in the order in section 5.

### Firm operating system: scope (Phase 2)
Each module is a small set of tables and routes in `app/ops/`, with the usual `practice_id` / `firm_id` checks, a denial test per route and audit-log entries. Ship time and budget (item 4) first, because the partner stage must measure time saved (section 1b); then the rest in this order:
1. **Clients and pipeline:** prospect, proposal sent, engaged, active, renewal due, lost. Extends `ClientProfileDetails` and `ClientContact`. Contact log for calls, emails and notes.
2. **Proposals and engagement letters:** fee quote from a practice price list, engagement letter from a template, client e-acceptance recorded in the audit log. Template wording comes from Quentin and the attorney, not invented.
3. **Staffing and scheduling:** auditor capacity per week, assignment with independence check (no conflicts recorded), engagement calendar with fieldwork and due dates.
4. **Time and budget:** time entries per engagement and stage, budget versus actual, and rework flag. This is also the measurement the vision needs.
5. **Billing and payments:** invoice from time or fixed fee, reminders by email (Resend), Stripe test mode behind a flag, then live only after Abdullah picks the account.
6. **People and credentials:** auditor licences and CPE expiry dates, alerts before expiry, and who may sign which audit type.
7. **Firm dashboard:** pipeline value, utilization, cycle time, overdue invoices. Practice-scoped; partner and admin only.

AI assist in the firm OS (drafting proposals, follow-ups, reminders) comes after the modules work and never sends anything on its own. Estimated new spend: $0 (Resend and Stripe test mode are free; Stripe live charges per transaction).

## 1b. Business model: AI-native service firm (Abdullah, 2026-11-20)

Abdullah's model, in his order:
1. **Partner stage.** Put Kien into existing audit firms and AML consultants. They run real engagements on it; Kien learns, fixes and improves from their use.
2. **Own firm.** Kien Solutions starts its own auditing practice.
3. **Hire 2 or 3 auditors** who run the same Kien workflow.
4. **Sell audits at market price.** Clients pay what they pay today. Because AI does much of the prep and the firm OS runs the business, each auditor completes more engagements with less overhead. That margin is the AI-native service business.

What each stage needs from the product:

| Stage | Product must have | Plan phase | Proof to move on |
|---|---|---|---|
| Partner | AML end to end, practice-vs-practice isolation proven on Postgres, partner branding, onboarding of a partner's own templates, feedback capture, and time and cycle measurement | Phases 1, 2 (time module first) and part of 5 | Two partners finish real engagements; their data is provably separate; measured hours per engagement |
| Own firm | Firm OS complete (pipeline, proposals, staffing, time, billing, credentials), signing-firm and signer stored per engagement, independence and QC records | Phase 2, then 5 | Quentin signs Kien's own engagements; firm runs without spreadsheets |
| Hire 2 or 3 auditors | Capacity view, assignment, reviewer-differs rule, credential tracking, training on the workflow | Phase 2 | New auditor completes an engagement in Kien with partner review |
| Market pricing | Price list per practice, time and margin per engagement, AI measured against human time | Phases 2 and 4 | Margin per engagement known from real data, not assumed |

Build consequences:
- **Time tracking and measurement move to the front of the firm OS** (Phase 2, item 4 first), because the partner stage is where the "AI saves time" claim gets tested.
- **Practice isolation must be proven before partner #1 touches real data** (readiness 23).
- **Partner data and IP stay the partner's.** Partner work must not seed Kien's own practice (templates, clients, eval sets) without written permission.

Open risks the model raises (need advice, not code):
- **Channel conflict:** once Kien runs its own firm it competes with its partner firms for clients. This needs partner agreements written with the attorney before the first partner signs ([VISION.md](VISION.md)).
- **"Same pricing" assumes** clients accept an AI-assisted audit at the normal price and that quality holds. Measure in the partner stage before relying on it **[inferred]**.
- Quentin's capacity as signing partner limits volume until more credentialed auditors join **[inferred]**.

## 2. What exists today vs. gaps

Source: `app/database/models.py`, `docs/kb/*`, `docs/readiness/STATUS.md`, migrations through `a130_ai_analysis`. Merged source is not proof of deployment.

| Capability | Today (in source) | Gap to "full firm backend" |
|---|---|---|
| Tenancy | Client `firms` (subdomain per client) plus a `Practice` (the auditing firm) with team roles, rubric and request templates (a121). Server-side `firm_id` and assignment checks; denial test per route. | Practice-vs-practice isolation tested only on SQLite-style cases, not a real second practice on Postgres (readiness 23, partial). No database row-level security **[inferred: defence in depth worth adding]**. |
| Audit types / many engagements | `Engagement` is one AML test; checklist is the YAML `aml_bd_v1`, 34 items, snapshotted per engagement. Rubric and templates are per practice. | **Biggest structural gap.** No "audit type" abstraction (procedure set, report template, credential and independence rules). AML-specific assumptions (34 IDs, restricted SAR IDs, client statuses) are wired in. |
| Client management (CRM-ish) | `ClientProfileDetails`, `ClientContact`, invitations, onboarding walkthrough (a116). | No lead/prospect stage, renewals, engagement history view, document of terms, or contact log. Twenty CRM is off-limits for Kien (brief section 6), so this stays in Kien. |
| Staffing, scheduling, time | Auditor assignment, `AuditorTask` (priority, due), pipeline board. | No capacity view, no time entry, no engagement budget, no calendar. Nothing to measure effort or rework (vision stage 2 needs it). |
| Billing | Invoices: draft/sent/paid/void, partial payments, per-issuer numbering, client invoice list, 6 currencies (a112). | Reminders and card payments are parked (Stripe not chosen). No engagement fee quote, retainer, or time-to-invoice link. |
| Document intake and sorting | Multi-file upload, SHA-256, ClamAV scan, R2 storage, per-item links, unassigned pool, bulk-then-sort UI (partly). | AI intake sorting not built. No OCR (scans skipped), no XLSX/DOC/XLS. |
| AI analysis | `ai_adapter/` + `audit_engine/`: up to 8 files, drafts with doc and page citations, SAR block (ID, tag, content scan), free-only price check, audit-logged (PR #137, off by default). | No compose service or outbound rule on the server yet; synchronous runs; double-click starts two; output quality unmeasured; rubric is DRAFT until Quentin approves. |
| FINRA / regulatory chatbot | Designed only ([kb/16](kb/16-ai-features-finra-chatbot.md)). | Not built. Needs Quentin's question set and the attorney's wording (readiness 11). |
| Report generation | Editable per-engagement report, per-item findings, sanitized rich text, finalize with attestation and SHA-256, audited reopen, DOCX/PDF draft. | Template wording and sign-off type unconfirmed by Quentin (readiness 27). Report is AML-shaped. No stored signed-PDF version with e-signature **[inferred]**. |
| Review / sign-off | Findings, response requests, reviewer-differs-from-preparer, engagement signoffs (a126), per-practice "assigned auditor may sign" setting (a128). | Independence and quality-control records are thin. No partner approval queue across engagements, no peer-review sampling. |
| Audit trail | SHA-256 hash-chained `audit_logs`, DB triggers block update and delete, chain verification, every AI call logged without text. | No external checkpoint of the chain head (readiness 21). Leftover firm cannot be deleted because of the immutable trigger (needs a documented erase-by-tombstone path). |
| Retention / erasure | `app/retention.py` export, plan, erase (bytes deleted, hashes and chain kept); `RECORD_RETENTION_DAYS=2190` placeholder. | Retention rules, legal hold and backup RPO/RTO are undecided (attorney, Abdullah). Not run against live storage. |
| SOC 2 groundwork | Auth and email codes, rate limits, scrubbed logs, upload controls, backup with test restore, security docs. | Readiness item 22 not started: no control list, policies, vendor register, access reviews, incident runbook, or evidence collection. Never claim certification. |
| Measurement | Audit log timestamps only. | No time-in-state, effort or rework metrics. |

## 3. Target architecture (current direction; AWS stays paused)

Keep what is deployed. Add modules, not new systems.

```
Cloudflare Workers (Next.js)  <- practice host + client subdomains, free tier
        |  HTTPS
Caddy -> FastAPI "kien-api" (app/)  <- workflow, tenancy, audit log, billing, reports
        |             |
 PostgreSQL 16     worker (checks, jobs)         Cloudflare R2 (files)
 (+ pgvector later)       |
                    ai_adapter (separate authenticated service)
                          |  outbound allowlist: openrouter.ai only
                      OpenRouter :free models (paid only on your approval)
```

Design rules for growth:
1. **Audit type as data.** New tables/config: `audit_types` (id, version, name), each with procedure set, request catalog (the YAML idea generalized), report template, role/credential rules, independence rules. `Engagement` gets `audit_type_id` + version. AML becomes audit type #1 with zero behaviour change (migration plus tests proving the 34-item flow is identical).
2. **Firm-ops as a thin new module** (`app/ops/`): time entries, capacity, engagement budget, renewal dates, client interactions. Plain tables, plain routes, same tenant checks and a denial test per route. No separate CRM product.
3. **One job queue** (the existing `check_jobs` pattern, generalized) so AI runs, OCR and report builds are async and idempotent (fixes double-click runs).
4. **Isolation in depth:** keep server-side checks and add Postgres row-level security on `practice_id` / `firm_id` as a second wall **[inferred; needs a spike]**.
5. **Self-hosting limits:** the VPS is 2 vCPU and 3.7 GiB RAM, already running database, scanner, API, worker, web. Adding OCR, an AI gateway and pgvector will likely need a larger VPS **[inferred]**. Do not change compose memory limits without your say (brief rule).
6. **No model calls in `app/`.** `tests/test_workflow_boundary.py` stays. All AI goes through `ai_adapter/`.

## 4. How AI fits: staged pattern (ICM)

ICM is a layout and contract method: each stage has Inputs, Process, Outputs and one Check; a person, script or test passes the check before the next stage ([ICM-PLAN.md](ICM-PLAN.md)). Kien already has this for the AI analysis ([pipelines/ai-analysis](pipelines/ai-analysis/CONTEXT.md): select evidence, SAR pre-screen, draft, validate, auditor review). The plan is to reuse the same shape for every AI task:

| Stage | Rule |
|---|---|
| 1. Select | Deterministic. Only files in scope for this firm and engagement. |
| 2. SAR pre-screen | Zero model calls. Block by ID, tag and content. Auditor sees what was skipped and why. |
| 3. Draft | Model call through `ai_adapter` only. Cheapest approved model. Every claim cites document and page. |
| 4. Validate | Script: citations resolve to real pages, no client-visible wording about findings, price and model allowlist checked. |
| 5. Human gate | Auditor accepts, edits or rejects. Partner approves findings; partner signs reports. Software never does either. |
| 6. Measure | Log model, version, tokens, cost, accept/edit/reject rates (no document text). Feeds the quality dashboard. |

AI tasks to add in this order (each is its own pipeline folder, own eval set, own flag, off by default):
1. Intake sorting (suggests checklist item per file; auditor confirms). Needs OCR for scans.
2. Analysis drafts (exists; needs quality measurement against Quentin's own reads).
3. Report drafting assist (section prose from accepted findings only; auditor edits).
4. FINRA/regulatory chatbot (public rules only, pgvector, citations or refuse, no client data, SAR terms refuse).
5. Ops assist (draft client emails, renewal reminders). Lowest risk, never sends on its own.

Standing limits: SAR never to any model; synthetic data until the real-document conditions in brief section 7; free models only in the trial; no model decides anything.

## 5. Phased roadmap

Rough sizes are builder-thread effort, not calendar promises. Spend is new monthly cost beyond today.

| Phase | Goal | Main work | Exit check | Est. new spend |
|---|---|---|---|---|
| 0. Finish the demo path (now) | Deploy-ready AI slice | AI compose service + openrouter-only outbound rule; smoke test; commit 7-step check script; post-demo hardening list (brief section 9) | Synthetic smoke test passes after your "go" | $0 |
| 1. AML real-use readiness | Run on Quentin's real files safely | Quentin approves rubric; OCR; XLSX; async queue; quality eval vs Quentin's blind test; readiness items closed; retention decided; backup/restore drill and off-site copy | Real run only with Quentin's OK and SAR-clean files; AI drafts measured against his reads | $0 to $10 (storage); VPS upgrade possible, see section 7 |
| 2. Firm operations | Run the practice day to day | Time entry, capacity view, engagement budgets, client interaction log, renewal dates, partner approval queue, measurement of cycle time and rework | One practice runs a quarter of engagements without spreadsheets | $0 |
| 3. Audit-type engine | Second audit type possible without a code fork | `audit_types` design spike, then migration of AML into it; procedure and report templates per type; per-type role and independence rules; second type only with a named credentialed lead | AML tests identical before and after; a second type configured by data only | $0 to $20 |
| 4. Intake sorting + report assist + chatbot | AI beyond analysis | Pipelines 1, 3, 4 above with eval sets from Quentin; pgvector; rule ingestion job | Each passes its eval gate; humans still approve | free models first; paid only on your OK (est. a few $ to tens of $ per month at low volume) |
| 5. Firm scale | Partners and own practice | Practice-vs-practice isolation proof on Postgres + RLS; independence and QC records; white-label branding; Stripe test-mode then live; peer-review sampling | Independent security review PASS; two practices cannot see each other | $10 to $60 (bigger VPS, email volume, Stripe fees per transaction) |
| 6. SOC 2 groundwork (runs alongside from Phase 1) | Evidence habits, not a certificate | Control list, policies, vendor register, access reviews, incident runbook, chain-head checkpoint, evidence folder | Written control matrix; "in progress" only, never "certified" | $0 until an auditor/tool is chosen (that is a decision) |

Phases 2 and 3 are the two long ones. Phase 6 items are small and should start in Phase 1.

## 6. Hard rules, restated for this plan
SAR never to any model. Mock data only until Quentin's written OK plus readiness items and your authorization. Humans approve findings and sign reports. No secrets in chat, code or logs. Approved neutral black-and-white look unchanged. No claim of AWS certifications; Kien SOC 2 is groundwork only. Partner firm data and IP are not Kien's by default; nothing from one practice trains, evals or informs another without written permission. Agents never deploy, SSH, change DNS or turn on `AI_ANALYSIS_ENABLED` in production without your "go". Max two build threads at a time.

## 7. Costs (estimates; verify before spending)

| Item | Now | After Phase 5 |
|---|---|---|
| Cloudflare Workers + R2 | free tier | free to a few $ |
| Resend email | free tier | free to $20 |
| OVH VPS | existing | one size up probably needed (price not verified; **unverified**) |
| Models | $0 (`:free` only) | $0 trial; paid only if quality demands it and you approve |
| Stripe | none | per-transaction fees only |
| SOC 2 tooling/auditor | none | optional; quote needed |
| Total new run cost | | roughly $10 to $60 a month plus the VPS step **[inferred]** |

## 8. Risks and honest unknowns
- Free-model quality is unmeasured; it may not be good enough, which pushes toward paid models (your decision).
- Readiness item 41 vs rule 10 (does attorney approval cover OpenRouter with real data) is still recorded as unresolved in [kb/19](kb/19-open-questions.md).
- Serving partner firms and running Kien's own practice may compete for clients; legal and commercial advice needed ([VISION.md](VISION.md)).
- "Largest AI-native audit firm across all auditing" needs credentialed leads and independence rules for each specialty; software cannot supply those, and methods may not transfer from AML **[inferred]**.
- Partners will adopt Kien, AI saves time, and Quentin has capacity: unproven.

## 9. Decisions for Abdullah (I have not decided any)
1. ~~Which layer leads after AML~~ DECIDED 2026-11-20: firm operating system.
2. Approve a design-only spike for the audit-type engine (no code until you OK it).
3. When may paid models be used, and with what monthly cap?
4. VPS size-up: when, and budget.
5. Stripe: account/entity and when to start test mode.
6. Retention period, legal hold and backup targets (needs attorney).
7. SOC 2: start groundwork now? Choose a tool or auditor later.
8. First second audit type, and who is the credentialed lead.
9. ~~Partner path vs own practice first~~ DECIDED 2026-11-20: partners first, then own firm with 2 or 3 hired auditors (section 1b). Still needed: partner agreement terms with the attorney (channel conflict, data and IP).

Needs Quentin: rubric, report template and sign-off type, 30 chatbot questions, blind-test engagement. Needs attorney: retention, model approval scope, partner data/IP terms.
