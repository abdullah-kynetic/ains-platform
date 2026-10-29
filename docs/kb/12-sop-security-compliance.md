# SOP — Security and compliance

## Non-negotiable rules
1. **SAR material never goes to any AI model.** SAR-related checklist items (AML-BD-017, AML-BD-025) are restricted: clients are told not to upload, uploads are rejected, handling is human-only. Any future SAR pre-screen starts with **zero model runs**.
2. **Mock/synthetic data only** in code, tests, demos, docs and screenshots. Never open real client documents.
3. **Ask permission before touching Abdullah's computer or documents** — or don't interact at all.
4. **No secrets** in chat, code, commits, logs, screenshots or `NEXT_PUBLIC_*`. Use variable names only. Never read `.env`.
5. **Client feedback never reveals audit findings** — only document issues.
6. **Humans approve findings and sign reports.** Every AI-produced finding (future) must cite document and page.
7. **Tenant isolation on the server** for every query; cross-tenant denial test per new endpoint.
8. Shared OVH box: never touch n8n, Twenty or the client portal.
9. Never claim AWS's or any vendor's certifications as Kien's. Kien is not SOC 2 certified; SOC 2 is groundwork only.

## Controls in place (from code/docs)
- Argon2 passwords, server-side revocable sessions, secure cookie flag, auditor TOTP MFA, hashed one-use recovery/reset/magic/invite tokens.
- Sign-in throttling (`auth_rate_limits`).
- Upload validation: type/extension, size ≤100 MB, zero-byte rejection, SHA-256, firm-scoped storage keys, restricted-item rejection.
- Hash-chained immutable audit log (DB triggers block edits). Limitation: a privileged DB admin could rewrite the chain; no external checkpoint.
- Sentry scrubbing to an allowlist (no bodies, cookies, URLs, emails, document data). PII/replay disabled.
- Report sanitizer keeps only plain formatting tags.
- Workflow boundary test blocks model SDKs in `app/`.

## Known gaps (residual risk)
- No malware scanning/quarantine on uploads. (Roadmap: security hardening.)
- No general API rate limits or lockout policy.
- No approved retention/deletion, backup schedule/restore drills, or legal hold on OVH.
- Secrets on OVH managed by hand; no secret manager or rotation policy.
- No formal security owner or incident process.
- No external audit-chain checkpointing.

## Compliance context
- **FINRA Rule 3310** (and CAB Rule 331): the independent AML test Kien supports.
- **Reg S-P** (SEC privacy/safeguards, amended 2024 with incident-response and customer notification requirements): applies to the broker-dealer clients; Kien as a service provider should support their obligations — encryption, access control, incident notification, vendor oversight. Exact contractual obligations need attorney input.
- **SOC 2**: groundwork in progress (policies, access reviews, logging, change management evidence from PRs/CI). Not certified.
- **BSA / FinCEN SAR confidentiality**: why SAR material is human-only.
- Insurance (E&O, cyber), entity and attorney review tracked in the Notion AML Audit OS hub.

## AI-specific
- Attorney verbally approved **Anthropic and OpenAI** as model providers. Use zero/limited data retention options where available.
- AI may only see public rules and approved non-client resources (chatbot) or, for intake sorting, client docs only after a separate approved data contract — never SAR.
- Log every AI question/answer/source; show a "not legal advice" note.
