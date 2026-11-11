# Pilot seed and e2e seed (L2-9)

Code: `app/pilot_seed.py`, `scripts/e2e_seed.py`, config `PILOT_INVITEE_EMAILS`. No migration.
Synthetic names only; nothing here prints a token, email or password.

## `python -m app.pilot_seed [--send]`

Creates what is missing, then changes nothing on re-runs:
- three synthetic firms: slugs `pilot-alpha`, `pilot-beta`, `pilot-gamma` (use these for the
  pilot host list in `web/wrangler.jsonc`);
- one practice ("Synthetic pilot practice") and one synthetic auditor
  `pilot-auditor@example.test` (team role partner), assigned to all three engagements;
- one engagement per firm (period 2025, due in 60 days) with the 34-item checklist initialized.

Invitations:
- Only for addresses in `PILOT_INVITEE_EMAILS` (comma separated, matched to the firms in order).
- Without `--send` they are created but not delivered. The auditor can resend them from the
  invitations screen, which issues a fresh link.
- With `--send`, each newly created invitation is emailed through Resend once. A failed delivery
  rolls that invitation back so the next run retries.
- Refuses to run if `ENV=production` and `INVITATION_PREVIEW_ENABLED` is on.
- The auditor gets a password only if `DEMO_PASSWORD` is set. Auditors still enroll MFA.

Running it with `--send` emails real inboxes: only do that with Abdullah's go-ahead and a Resend
key. This build ran the seed only against in-memory test databases, with the email call replaced.

## `scripts/e2e_seed.py`

`seed_workflow_fixtures(session)` (or `uv run python -m scripts.e2e_seed`) adds a separate firm,
`kynetic-flow` (browse at `http://kynetic-flow.localhost:3100`), with its own auditor, reviewer,
partner and client, so the original `e2e-auditor` still sees exactly one engagement.
Logins use the same test-only passwords and TOTP secret as `scripts/e2e_backend.py`:
`flow-auditor`, `flow-reviewer`, `flow-partner` (all `@example.test`, auditor password) and
`flow-client@example.test` (client password).

| Engagement (period year) | State |
|---|---|
| `testing` (2021) | nothing concluded, one receipt-only document, no findings |
| `ready` (2022) | all items concluded, workpaper reviewed, samples tested, independence cleared, one finding released and answered: no blockers, reviewer approval can start |
| `signed` (2023) | reviewer approved, partner signed, completed; client has not confirmed |
| `confirmed` (2024) | as signed, client confirmed, one sent invoice |

Refuses a Postgres `DATABASE_URL`. Lane 1 calls it from a hook; it does not edit
`scripts/e2e_backend.py`.

## Decisions to review

- Pilot invitations are created without delivery by default. Say if you want `--send` to be the
  default once the Resend key exists.
- The pilot auditor is a synthetic stand-in. Quentin's real account is invited, not seeded.
- The pilot seed refuses only the preview flag in production; it does not refuse production
  itself, because the pilot firms are meant to live there. The names say "(synthetic)".
