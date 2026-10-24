# Audit log

`a110_audit_chain` extends the existing `audit_logs` table and deterministically
backfills historical rows in timestamp/ID order. Historical IPs remain unknown.
New events include the direct request peer IP; background events have no IP.
No forwarded headers are trusted. Existing login, upload, feedback, manual
review, finding decision, and report draft events are chained automatically.
Engagement/workspace/evidence queue reads also record view events.

Each firm has an independent chain; authentication events without a firm use a
separate system chain. SHA-256 covers the row ID, tenant, actor, action, target,
details, UTC timestamp, IP, sequence, and previous hash in canonical JSON.
A transaction advisory lock serializes appends on Postgres. Events commit in the
same transaction as edits. ORM flush and bulk statement guards reject mutations;
the Postgres migration adds a trigger rejecting UPDATE, DELETE, and TRUNCATE.
The application database role must not own the table or have DDL/trigger bypass
privileges. Hash chains detect altered values and missing intermediate entries;
a privileged administrator who disables protection and rewrites the entire chain
can defeat verification. External checkpoints would be needed to detect that.

Auditor endpoints:

- `GET /auditor/audit-log?firm_id=...`: descending sequence, `limit` (1–100),
  `offset`, exact `action`, `actor_id`, `entity_type`, `entity_id`, optional
  `engagement_id` (includes related requests, documents, findings, and tasks),
  and inclusive `since`/`until` timestamp filters. Returns `items` and `has_more`.
- `GET /auditor/audit-log/verify-chain?firm_id=...`: verifies the complete firm
  chain, returning `valid`, `checked`, and `broken_at`.
- `POST /auditor/engagements/{id}/report/signoff`: explicit assigned auditor
  action requiring `reportSha256` and `attestation: true`; only available while
  awaiting signature. Records approval of that artifact hash and completes the
  engagement. It does not create a cryptographic document signature.

Firm history and verification require auditor assignment to every engagement in
that firm, so firm-wide results cannot expose unassigned engagement activity.
System authentication chains are not exposed through firm APIs. Client roles
cannot access any of these endpoints. Demo UI data and verification are explicitly
synthetic. The auditor page lives at `/auditor/audit-log`.

Run `uv run pytest` and the web lint/typecheck/build/Playwright scripts.
The Postgres integration test starts a private temporary cluster with no TCP
listener when local Postgres binaries are installed; otherwise it is skipped.
