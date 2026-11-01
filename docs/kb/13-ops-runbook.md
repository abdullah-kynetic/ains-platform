# Ops runbook (current OVH setup)

## Where things are
- Server: OVH VPS `40.160.150.91`, user `ubuntu`. Kien in `/opt/kien`, Docker compose project `kien` (API container `kien-api-1`, Postgres container, Caddy). **Shared**: n8n, Twenty, client portal also run here — never touch them.
- Frontend: Cloudflare Workers (see `04-tech-stack-and-vendors.md`).
- Files: R2 `kien-dev-documents`. Email: Resend.

## Daily / routine
- Health: `curl https://api.kiensolutions.com/health` and load live/preview addresses.
- Containers: `docker compose -p kien ps`, logs `docker compose -p kien logs --tail 200 api` (never paste secrets/payloads).
- Worker queue: check `check_jobs` for stuck `running`/`failed` rows (read-only SQL).
- Disk: `df -h`; DB dumps accumulate in `/opt/kien/*.dump` — prune with approval only.

## Incidents
| Symptom | First steps |
| --- | --- |
| Site won't load | Check Worker deployment (`wrangler deployments list`), DNS, try private window/other network |
| API 5xx | `docker compose -p kien ps/logs`; recent deploy? → roll back with `rollback-<tag>.yml` |
| Bad frontend release | `wrangler rollback <previous-version> --name <worker> -c <config>` |
| Emails not sending | Resend dashboard status; missing key → 503 from email endpoints |
| Upload failures | R2 status, API logs, file size/type errors |
| Data issue after migration | Stop, take a fresh dump, restore previous dump only with approval |
| Suspected breach | Revoke sessions, rotate `SESSION_SECRET`/keys, preserve logs, tell Abdullah immediately; Reg S-P notification duties may apply to clients |

## Backups
Today: ad-hoc `pg_dump -Fc` before each deploy (in `/opt/kien`). **No scheduled backups, off-site copy, or restore drill confirmed on OVH** — top ops gap. AWS plan adds daily dumps to S3 (14 days).

## Demo accounts
Two synthetic demo logins (client + auditor). Credentials live only in a file on Abdullah's Mac and on the box; never in chat. Reset walkthroughs only for explicit demo runs.

## To build (roadmap item 2)
Proper runbook with alerts (uptime, queue age, disk), scheduled encrypted off-site backups, restore drill, secret rotation, log retention.
