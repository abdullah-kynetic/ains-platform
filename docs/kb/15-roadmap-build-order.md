# Roadmap and build order

## Current authorized sequence

1. Cleanup: repair browser tests, correct Quentin's spelling and refresh documentation.
2. Backend for the new mock screens, in small stacked slices: clients/contacts/summaries; checklist/documents; workpapers/samples; findings/released requests; reports/export; independence/review/sign-off; firm settings; notifications/search; client results.
3. Restore web auth, MFA, invitations, setup, reset and sign-out; refuse host/role mismatch. Keep unauthenticated demo only under USE_MOCKS. No deployment.
4. Security hardening: quarantine/scanning, API limits/lockout, operations instructions, off-site backup scripts and restore drill. Local/config work only.
5. Invoice follow-ups and test-mode Stripe behind an off-by-default flag.
6. AWS preparation: infrastructure/config/runbooks only. Do not apply or create resources.

The earlier roadmap numbered invoicing 1, security 2 and AWS 4; the sequence above is Abdullah's current request. No model processing or other AI feature belongs to this work.

## Existing state

PRs #53–#60 and #64–#72 are merged. The neutral design is approved. New screen contracts remain synthetic until their backend slices are delivered; see [frontend inventory](../frontend-inventory.md). Web auth is temporarily removed. Current deployed code and database were not inspected.

## Decisions

Abdullah decides Stripe account/entity and payment methods, AWS target/budget, backup and retention objectives. Quentin supplies rubric, severity and report wording; legal terms require the attorney. Keep unresolved inputs visible rather than inventing them. No live deploy, OVH operations, production migration or merge is authorized.
