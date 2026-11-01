# Open questions (need a decision)

## For Abdullah
1. Approve visuals on preview (#53–#58, #60 — still unmerged) and layout (#59)? Fold the layout into the live build?
2. Design branch #50 (design.kiensolutions.com): keep exploring, or close?
3. Can a client undo an N/A the auditor set? (Recommended: yes.)
4. AWS: send sign-in code after root MFA. Target shape: single EC2 (cheapest) vs RDS from day one?
5. Stripe: which account/entity, and which payment methods? Fees passed to clients?
6. Monthly budget cap for hosting and AI.
7. GitHub: create a fine-grained token that can open PRs (gh currently can't).
8. Retention/deletion policy and backup targets (how much data loss is acceptable, how fast to restore).
9. Who is the product owner of record and security owner (for SOC 2)?

## For Quentin
1. Audit rubric wording, applicability conditions and allowed evidence types for each of the 34 items (fields intentionally empty).
2. FINRA/AML resources for the chatbot and ~30 common client questions with model answers.
3. Report template wording and sign-off procedure (is hash attestation enough, or a real e-signature?).
4. Severity logic and sample (sanitized) report.

## For the attorney
1. Written confirmation that Anthropic and OpenAI are approved, and under what retention terms.
2. Reg S-P service-provider obligations and client contract terms (incident notice timing).
3. "Not legal advice" wording for the chatbot.

## Technical unknowns
1. `/tenant/branding` backend route not found — confirm per-firm branding works in real mode.
2. How `kien-demo-live` is configured (repo `wrangler.jsonc` says `ains-platform-demo`).
3. Is Sentry enabled in production?
4. R2 credential variable names on OVH (not in `.env.example`).
5. Scheduled backups on OVH — do any exist?
