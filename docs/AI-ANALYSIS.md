# AI analysis (Stage 3, demo slice)

Status: branch work under Abdullah's Stage 3 authorization (2026-11-11). Not deployed. Synthetic data only. Fake model in all tests.

## What it does
On an engagement, an auditor clicks **Run AI analysis** (Findings tab). The API reads up to 8 uploaded files (PDF, DOCX, TXT, CSV), each with the checklist item it is linked to, and asks an authenticated AI service for drafts: possible findings, document flags and suggested client requests. Each draft cites a document and page and lands as **pending**. The auditor can **Accept**, **Edit** or **Reject**.

Accept only copies the draft into an ordinary *draft* finding (internal). It still needs the existing approval and "Request response" release before a client sees anything. No client route returns drafts, runs or findings.

## Switch and settings (names only, no values in the repo)
| Variable | Where | Meaning |
|---|---|---|
| `AI_ANALYSIS_ENABLED` | API | Default `false`. Off means every AI route returns 404 (after the 401/403 checks) and the button is hidden. |
| `AI_SERVICE_URL` | API | Private address of the AI service. |
| `AI_SERVICE_TOKEN` | API and AI service | Shared credential the API presents to the AI service. |
| `OPENROUTER_API_KEY` | AI service only | Never in the API, the repo, logs or errors. |
| `AI_ENABLED` | AI service | Existing flag, default `false`. |
| `AI_OWNERSHIP_DATABASE_URL` | AI service | Read-only database URL used to verify, on every call, that the document belongs to the stated engagement and firm. Empty means every call is refused. |
| `AI_STATE_DATABASE_URL` | AI service | Holds the durable call log (`ai_call_log`) plus counters. |

## Safety layers (all before any model call)
1. Restricted checklist items (AML-BD-017, AML-BD-025, from the canonical catalog) and SAR tags. A file linked to a restricted item is not even read from storage.
2. Content scan (`ai_adapter/guards.sar_content_reason`): blocks any mention of SAR, suspicious activity report/filing/narrative, suspicious transaction report, FinCEN Form 111. Handles case, punctuation, spacing, full-width letters and zero-width characters. Runs on the file name and the extracted text (PDF text included), in the engine and again inside the adapter. Blocked files are skipped and the auditor sees why. This is deliberately aggressive: a policy that merely names its SAR procedure is skipped too, and a person reads it.
3. Scope and ownership: every adapter call carries firm, engagement and user. The adapter verifies the document belongs to that engagement and firm, or refuses.
4. Models: only exact `:free` IDs on `ai_adapter/allowlist.json`, price-checked to exactly zero on each call, no routers, no `:online`, no paid fallback, provider data collection denied. The second model is tried only after an upstream failure, never after a policy refusal.
5. Outbound: the adapter refuses to start unless the model base URL host is in `AI_ALLOWED_HOSTS` (default `openrouter.ai` only). The compose overlay puts the service on its own `ai_egress` network (10.77.40.0/24) and `deploy/ai/egress-firewall.sh` limits that subnet to `openrouter.ai` on 443 plus DNS. The rule matches the IPs the name resolves to when it is run, so re-run it after any DNS change.
6. Output is re-validated: fixed JSON, three draft kinds, cited document must be the one sent, page must exist, no status/sign/approve fields (extra fields discard the whole reply).

## Audit trail
- Adapter: one `ai_call_log` row per attempt (firm, engagement, user, document id, item, model, prompt version, outcome, code, token counts, time). No text.
- API: `ai_analysis.run` and `ai_draft.accepted|edited|rejected` rows in the firm's hash-chained audit log, ids and counts only.

## Draft rubric
`audit_engine/rubric_draft.yaml` is marked **DRAFT, needs Quentin's approval** and covers CIP (AML-BD-009), CTR/large cash (AML-BD-012), monitoring (AML-BD-004), training (AML-BD-003) and independent testing (AML-BD-021). It is prompt context for drafting only. The canonical checklist's rubric placeholders are untouched.

## Not done / for later
- The AI service is **prepared, not deployed**: `deploy/docker-compose.ai.yml` (additive overlay), `deploy/ai/` (env names, read-only role, egress rule) and the entry point `ai_adapter/main.py`. Until it runs, `POST .../run` returns 503. Deploy steps and the synthetic smoke test: `docs/demo/AI-SMOKE-TEST.md`.
- One run per engagement at a time: a second click or tab gets 409. This guard is in-process, so the API must stay a single process (it is, today).
- Runs are synchronous (up to 8 files); a background job is better if free models are slow.
- Images and scanned PDFs are skipped (no OCR). XLSX/DOC/XLS are skipped.
- Live OpenRouter was never called; the two model IDs were taken from OpenRouter's free-model collection page on 2026-11-11 and are re-checked by the price guard at call time. Output quality is unmeasured.
- Playwright check `web/e2e/ai-analysis-hidden.spec.ts` was written but not run locally (browser version mismatch in the build container).
