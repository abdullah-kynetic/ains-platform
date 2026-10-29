# Roadmap and build order

## Now (waiting on Abdullah)
- Visual review (all unmerged, not on `main`): preview.kiensolutions.com (#53–#58, #60), layout.kiensolutions.com (#59), design branch #50.
- After approval: merge in stack order with real merge commits → deploy `kien-demo-live` → verify both demo logins.
- Decision: may a client undo an N/A the auditor set? (Recommended: yes, keep.)
- AWS: root sign-in + MFA, send sign-in code.

## Build order (agreed)
1. **Invoicing follow-ups + Stripe behind a feature flag** — reminders/overdue follow-ups (no email today), Stripe payment links/checkout off by default, webhook → payment recorded as invoice event.
2. **Security hardening** — malware scan on uploads (e.g. ClamAV sidecar, quarantine state), general API rate limits/lockout, operations runbook + scheduled off-site backups + restore drill.
3. **Doc fixes** — reconcile OVH vs AWS conflicts in ARCHITECTURE/PRD/SECURITY, "Quinton" → "Quentin" in current-context text, de-duplicate appended sections, document `/tenant/branding` gap.
4. **Move to AWS** — per `14-aws-migration-plan.md`.
5. **Old PRs + better GitHub key** — triage stale `codex/*` and `cursor/*` branches; fine-grained token that can open PRs.
6. **SOC 2 groundwork** — policies, access reviews, change-management evidence, vendor list, logging/retention decisions.
7. **AI last** — (a) intake file sorting into the 34 items with auditor confirmation, SAR never to models; (b) FINRA rules chatbot. See `16-ai-features-finra-chatbot.md`.

## Dependencies
- 4 (AWS) should follow 2 so backups/runbook exist first; needs the AWS sign-in code.
- 7 needs 4 (pgvector on the new DB is easiest) and Quentin's resources/questions; needs an approved data contract for intake sorting.
- 1 needs Stripe account decision; 6 benefits from 4 (CloudTrail etc.).
