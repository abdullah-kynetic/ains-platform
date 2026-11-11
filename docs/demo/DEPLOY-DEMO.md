# Deploy the demo to the VPS: exact steps

Status: **not run.** The code agent has no SSH client, no key and, by `AGENTS.md`, never touches servers.
Everything below is ready to run by someone with SSH to `135.148.219.175` (API at
`api.kiensolutions.com`). Nothing here changes DNS, compose files or memory limits, and nothing prints
a secret. Synthetic data only. The old shared server (`40.160.150.91`) is not involved.

Facts taken from the repo, not verified on the server: compose project `kien` in `/opt/kien`, stack in
`deploy/docker-compose.prod.yml`, secrets in `/etc/kien/kien.env`, image published to GHCR by the
**Image** workflow after CI passes on `main`, deployed by digest.

## What Abdullah decides first

1. **Isolation screen on the live demo.** To show a real cross-firm denial it needs
   `ISOLATION_PROBE_ENABLED=true` in `/etc/kien/kien.env` (not a secret). Leave it off and the screen
   says plainly that it used a random id.
2. **Walkthrough step 1 (invite a client).** The invitation link is shown on screen only when
   `INVITATION_PREVIEW_ENABLED=true`, which the app refuses in production seeding paths and which
   returns links in API responses. Live email is skipped, so either enable preview for the demo
   window and turn it off after, or use the pre-created client contact the seed makes and skip step 1.
   I did not decide this.
3. **Frontend.** The web app deploys to Cloudflare Workers with `npm run deploy:production` from `web/`
   (builds with `NEXT_PUBLIC_API_URL=https://api.kiensolutions.com`, no mocks). It needs Wrangler
   credentials this session does not have. Note the previous Worker version first
   (`wrangler deployments list`) so it can be rolled back.

## Backend, in order

On the server, as the docker user, in `/opt/kien` with this repo checked out at the merged `main`
commit (`git -C /opt/kien pull --ff-only origin main` is not a rebase and keeps merge history).

1. Find the image digest: GitHub, Actions, **Image** workflow for the main commit, "Image digest"
   in the run summary. It looks like `ghcr.io/abdullah-kynetic/ains-platform@sha256:<64 hex>`.
2. (Optional) add the demo flag line to `/etc/kien/kien.env`: `ISOLATION_PROBE_ENABLED=true`.
3. `scripts/deploy-demo.sh deploy ghcr.io/abdullah-kynetic/ains-platform@sha256:<digest>`
   - takes a validated `pg_dump` first (`/opt/kien/kien-db-<tag>.dump`, mode 600),
   - writes `/opt/kien/rollback-<tag>.env` holding the image running now,
   - pulls, runs `alembic upgrade head` (migrations `a128` adds `practices.allow_auditor_as_signer`; `a129` adds `email_sign_in_codes` and `trusted_devices`),
     recreates `api` and `worker` only, and waits for the API health check.
4. Public check: `curl -sI https://api.kiensolutions.com/health` should show `200` and the security
   headers (HSTS, `X-Frame-Options: DENY`, `Content-Security-Policy`, `Referrer-Policy`,
   `Permissions-Policy`).
5. Seed: `scripts/deploy-demo.sh seed`. It refuses if the database holds any firm other than the two
   demo firms. Sign-ins are written to `/opt/kien/demo-credentials-<tag>.txt` (mode 600). Demo accounts
   have no authenticator (the seed switches any old enrollment off). Delete that file after the demo.
6. Frontend deploy (item 3 above), then run the walkthrough (`DEMO.md`) against the live URL and fill in
   `docs/demo/LIVE-RUN.md`.

## Sign-in settings (emailed code replaces the authenticator app)

After email + password, staff and clients get a 6-digit code by email (10 minutes, single use, rate
limited) and can remember the browser for 30 days. Settings go in the **app** env file (on the server
that is `/etc/kien/app.env`; the older single-file layout used `/etc/kien/kien.env`). Names only here.

| Variable | Needed? | Meaning |
|---|---|---|
| `RESEND_API_KEY` | secret, set by whoever has it | Resend key. **Leave unset for the demo as it stands** (live email is skipped): sign-in is then email + password only. |
| `EMAIL_FROM` | with the key | Verified sender, for example a Kien address on the Resend domain. |
| `EMAIL_SIGN_IN_CODES` | optional, default `true` | Set `false` to force password-only even when a key exists. |
| `PORTAL_URL` / `PORTAL_BASE_DOMAIN` | already set | Unchanged. |
| `SESSION_COOKIE_SECURE` | must be `true` in production | Also makes the remembered-browser cookie `Secure`. |
| `EMAIL_CODE_TTL_MINUTES` (10), `EMAIL_CODE_MAX_ATTEMPTS` (5), `EMAIL_CODE_RESEND_SECONDS` (30), `EMAIL_CODE_MAX_SENDS_PER_HOUR` (5), `TRUSTED_DEVICE_DAYS` (30) | optional | Defaults shown; leave alone. |

What to expect on the server:

- **No Resend key (the demo):** nothing to do. Every sign-in logs the warning
  `Email sign-in codes are OFF: RESEND_API_KEY / EMAIL_FROM are not set ...`. That line is expected.
  `GET /auth/capabilities` returns `"email_code": false`.
- **With a key and sender:** the sign-in screen shows a code step; `"email_code": true`. Test with a
  throwaway address you control before real users.
- Run the migration first (`a129`, additive). `AUDITOR_MFA_ISSUER` and `AUDITOR_MFA_ENROLLMENT_TTL_MINUTES`
  are no longer read; they can stay in the file harmlessly.
- Demo accounts: re-run `scripts/deploy-demo.sh seed`-style seeding is not required, but running the seed
  again switches off any authenticator already enrolled on the demo auditors (it creates nothing that exists).
- Audit log entries to look for: `auth.email_code_sent`, `auth.email_code_accepted`,
  `auth.email_code_failed`, `auth.device_remembered`, `auth.device_revoked`.
- Not tested live: the real Resend delivery path (tests use a fake sender).

## Rollback

`scripts/deploy-demo.sh rollback /opt/kien/rollback-<tag>.env` puts the previous image back. Safe
because migrations are additive. For a damaged database, restore the dump with `pg_restore` (ask
first). Frontend: `wrangler rollback <previous-version-id>`.

## What was not checked

The script has only had a syntax check (`bash -n`). Names such as the `postgres` and `api` services and
`deploy/lib.sh` come from the repo files and may differ on the server. Stop at the first surprise.

## What the server actually runs (checked 2026-11-10)

The script above was written from the repo, and the server differs. The deploy was done with the
server's own scripts instead:

- Compose interpolation file is `/etc/kien/compose.env`; secrets are split per service
  (`postgres.env`, `migrate.env`, `app.env`, `ai.env`). There is no `/etc/kien/kien.env`.
  App flags such as `ISOLATION_PROBE_ENABLED` go in `/etc/kien/app.env`.
- Images are built on the host (`deploy/build-on-host.sh <sha>` from `/opt/kien/src/<sha>`), tagged
  `kien-api:sha-<12>`, not pulled from GHCR by digest.
- Deploys use `/opt/kien/deploy/deploy.sh <image>` (backup if a migration is pending, migrate, roles,
  `api worker caddy`, health check). The server's `deploy/` folder comes from branch
  `lane1/l1-3-deploy-single-env`, which is not on `main`; `main`'s `deploy/` would drop the memory
  limits, so it was not copied over.
- `deploy.sh` hung in `restic forget` because the R2 bucket's object lock refuses deletes (it only
  happens when a second backup is taken on the same day). The database snapshot was already saved;
  the forget was stopped and the remaining deploy steps were run by hand.
- The seed runs with `docker compose ... run --rm -T --no-deps api python -m app.demo_practice_seed
  --confirm-synthetic-demo --credentials-file -`, redirected to a private file.
