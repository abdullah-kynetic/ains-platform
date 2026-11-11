# Live demo run

**Status: backend run on the live server, 7 of 7 API steps passed. The web screens were NOT run live**
(see "Web app" below). Run on 2026-11-10 at about 21:30 PST, by the operator agent, synthetic data only.

## What is deployed

| Part | Value |
|---|---|
| Commit | `664bd2539b620afa1fc1bb3415dcd4b40e4bd080` (main, merge of #133) |
| API image | `kien-api:sha-664bd2539b62`, image id `sha256:34ec80caadd06698039eb03f77e8ed7c4d18448e7eaf4eead117a995306f4929`, built on the VPS with `deploy/build-on-host.sh` |
| Previous image (rollback) | `kien-api:sha-5512a598371f` (recorded in `/opt/kien/releases/previous-image` and `/opt/kien/releases/rollback-demo-664bd25.env`) |
| Database | migrated `a117_response_requests` to `a128_practice_signoff_setting` |
| Backup before deploy | `pg_dump` at `/opt/kien/backups/kien-db-demo-664bd25-20261111050802.dump` (mode 600, 24 table-data entries) and restic snapshot `b203c264` |
| Demo flags (`/etc/kien/app.env`) | `ISOLATION_PROBE_ENABLED=true`, `INVITATION_PREVIEW_ENABLED=true` (turn both off after the demo) |
| Health | all five services healthy (`postgres`, `clamav`, `api`, `worker`, `caddy`); `https://api.kiensolutions.com/health` returns 200 |

## Results (live API, real Postgres, ClamAV and R2)

Scripted against `https://api.kiensolutions.com` with the same calls the screens make. Automated
time, not a human timing.

| Step | What | Seconds | Result |
|---|---|---|---|
| 1 | Workspace for a new firm, invitation in preview mode, client accepts and signs in | 2.7 | Pass |
| 2 | Send the checklist (34 requests); second send 409; other firm 404; client 403 | 0.7 | Pass |
| 3 | Two reasoned N/A requests; old direct N/A refused (409); client cannot decide (403); one approved, one rejected with a note | 1.8 | Pass |
| 4 | Three uploads numbered 1.1 to 1.3 (ClamAV scan, R2), map, unlink, submit, accept | 4.4 | Pass |
| 5 | Flag, client reply, resolve; finding with a response request, client answers without seeing the finding, finding closed | 2.2 | Pass |
| 6 | 34 conclusions, independence, second-reviewer approval, partner signature (Quentin), complete, client confirms the signed report, invoice created and sent, client sees it | 14.6 | Pass (see note) |
| 7 | Isolation probe and audit log | 1.6 | Pass |
| | **Total** | **about 30** | **7 of 7** |

Note on step 6: the first attempt did every action, then the script failed reading the
fingerprint (wrong response key in the script, not an app error). It was resumed against the same
engagement and finished. The "preparer cannot approve their own file" check therefore did not run
live; it is covered by the CI tests.

Isolation: `/auditor/isolation-probe` returned a real engagement of the second demo firm. Eight
requests for it (five auditor routes, three client routes) were all refused with 404, and the
auditor's own engagement still loaded (200).

Audit log: for the run's firm, `report.confirmed` 1 entry, `signoff.reviewed` 1 entry, and
`verify-chain` returned `valid: true` over 80 entries.

Security headers: present on the API (`Content-Security-Policy: default-src 'none'; frame-ancestors 'none'`,
HSTS, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`, `Permissions-Policy`, `nosniff`).
The web build carried CSP, HSTS, `X-Frame-Options: DENY`, `Referrer-Policy` and `Permissions-Policy`
while it was briefly deployed (below).

## Web app: not live yet

The web app on `main` serves each firm at `<slug>.kiensolutions.com` and auditors at
`auditor.kiensolutions.com`. It asks the API for the firm's branding from the browser's address, and
the API only answers that when `PORTAL_BASE_DOMAIN=kiensolutions.com` is set. Those hosts do not exist
yet (no wildcard DNS record or Worker route), so on any existing host the app shows "Unknown firm".
It was deployed to `preview.kiensolutions.com` (Worker `kien-signin-preview`), showed "Unknown firm",
and was rolled back to the previous version `d3c14558-f4b2-4cf8-ac0a-13b7e2ab6cdd`.

`npm run deploy:production` has no `--env production`, so as written it would replace the
`ains-platform-demo` Worker on `demo.kiensolutions.com`. With `--env production` it creates a new
`ains-platform` Worker with no route.

To make the screens live (needs Abdullah's approval, it is a DNS change):

1. Proxied wildcard DNS record `*` (placeholder address, as in `web/README.md`), leaving `api` DNS-only.
2. Worker route `*.kiensolutions.com/*` to the portal Worker; apex and `www` stay on the landing Worker.
3. On the server, `PORTAL_BASE_DOMAIN=kiensolutions.com` and `PORTAL_URL=https://{slug}.kiensolutions.com`
   in `/etc/kien/app.env`, then recreate `api` and `worker`.
4. Deploy the production build to the portal Worker and run `DEMO.md` by hand on
   `auditor.kiensolutions.com` and `demo-securities.kiensolutions.com`.

## Left on the server by this run (synthetic)

Firm `synthetic-live-run-securities` with one completed engagement, a client contact and one invoice.
The seeded demo practice (`demo-securities`, `demo-other`, Quentin, the reviewer and the client
contact) is untouched and ready for the walkthrough. Because a third firm now exists, the demo seed
will refuse to run again until that firm is removed.
