# AWS deployment runbook (lean single-host profile)

Low-volume, single-region production for Kien Solutions (AINS). Not a certification
or high-availability service. Quinton must approve control evidence, retention policy
and release before client use. Use synthetic documents for every smoke test.

## Design and tradeoffs

`infra/aws` runs everything on **one ARM64 EC2 t4g.micro** (1 GB RAM, 2 GB swap,
20 GB encrypted gp3): Caddy (HTTPS), the API, the receipt worker and **PostgreSQL 16
on localhost** (tuned for 1 GB: 128 MB shared_buffers, 30 connections). There is no
RDS, NAT gateway, load balancer, Secrets Manager or customer KMS key. The security
group opens only 80/443; Postgres and the API bind loopback; administration is via
SSM Session Manager (no SSH). Burst credits use `standard` mode so CPU can never bill
surplus credits.

- **Secrets**: SSM Parameter Store SecureStrings under `/ains-prod/` (free standard
  tier, AWS-managed key). The instance generates `SESSION_SECRET` and `DB_PASSWORD`
  on first boot, so no secret value is in Terraform state or user-data. Add
  `/ains-prod/RESEND_API_KEY` yourself to enable email, then
  `sudo systemctl restart ains ains-worker`. Without it email endpoints return 503.
- **Storage**: documents bucket (AES256, versioning, Object Lock enabled with no
  default retention; noncurrent versions expire after 365 days) and one `-ops`
  bucket for S3 access logs (`logs/`, 90 days), CloudTrail (`AWSLogs/`, 90 days),
  daily DB dumps (`backups/`, 14 days) and release bundles (`releases/`, 90 days).
- **Audit**: one multi-region management-events CloudTrail trail (the first one is
  free). Billed S3 data events are off (`trail_document_data_events`).
- **Backups**: `ains-backup.timer` runs `pg_dump -Fc` daily at 09:30 UTC to
  `s3://<ops>/backups/`. There is no point-in-time recovery; worst-case data loss is
  one day. Restore procedure, including the synthetic count drill:
  [backup-restore.md](backup-restore.md).
- **Image**: with `app_image` empty, Terraform uploads a `git archive` bundle to the
  ops bucket and the host builds the image locally (no registry). A new bundle
  replaces the instance (user-data changes), so **dump the DB first**; the EIP and
  SSM secrets survive, but the root volume and local Postgres do not.

Tradeoffs: one host, no failover; a host loss means restoring the last daily dump.
Move Postgres to RDS and add redundancy once client volume justifies ~$15+/month more.

## Provision

1. AWS CLI v2 + Terraform >= 1.7, authenticated to the target account. Keep the
   monthly budget alarm (currently `kien-monthly-15`, $15) in place.
2. Use a fresh per-account local state path; never reuse another account's state:

   ```sh
   D=$HOME/ains-state/<account-id>
   git archive --format=tar.gz -o $D/ains-source.tar.gz HEAD
   cd infra/aws
   terraform init -backend-config=path=$D/terraform.tfstate
   terraform plan -var-file=$D/terraform.tfvars -out=$D/tfplan
   terraform apply $D/tfplan
   terraform output
   ```

   See `terraform.tfvars.example`. Empty `api_domain` uses `<ip>.sslip.io` so Caddy
   gets a certificate before real DNS exists.
3. Bootstrap takes ~10–15 minutes (dnf, Postgres init, image build). Follow it with
   SSM: `sudo tail -f /var/log/ains-bootstrap.log`. The API container runs
   `alembic upgrade head` on start.
4. Synthetic demo data only (never in a database holding real client records):
   `sudo docker exec ains-api python -m app.demo_seed`.
5. DNS: add `A api.<domain> -> api_ip` (DNS only / grey cloud), set
   `api_domain = "api.<domain>"`, and re-apply (replaces the host; dump DB first), or
   edit `/etc/ains/Caddyfile` on the host and `sudo systemctl restart ains-proxy`.
6. Verify `https://<api_domain>/health`.

## Storage and retention behavior

`STORAGE_BACKEND=s3` is the application default and primary storage in settings,
`.env.example` and Terraform. No Egnyte subscription, account or credentials are
required. The Egnyte connector remains available only with an explicit
`STORAGE_BACKEND=egnyte`; its development path guard stays under `/Shared/AINS-Dev`.
S3 objects use `firms/{firm_id}/{engagement}/{item}/{random_id}-{filename}`.
The legacy DB column `egnyte_path` stores the opaque `s3://bucket/key` receipt so
existing APIs remain compatible. The worker checks the receipt's firm prefix
before reading. Switching providers does not migrate existing objects: migrate
and verify receipts separately before switching an existing deployment.

`S3Storage.put(..., final_report=True)` applies configured `S3_RETENTION_DAYS` and
`S3_RETENTION_MODE` to that object version. `0` disables per-object retention.
The bucket always supports Object Lock and versioning, but has no blanket retention
rule, so intake and unsigned drafts do not acquire final-report retention. The
current reporting workflow only generates unsigned drafts. A human-approved final
report workflow must call that storage operation after auditor approval; this
change adds no automatic signing or finalization endpoint. Verify the exact version's
retention after a synthetic final-report storage test. Retention does not protect
against writing a newer version; preserve the finalized version ID in the eventual
human approval record.

`S3Storage.presign(firm_id, path, upload=...)` provides short-lived GET/PUT URLs
(default 300 seconds, maximum 900). PUT clients must send the matching
`x-amz-server-side-encryption` header and KMS key header if configured. URLs are
bearer credentials: do not log them. These are internal adapter methods, not public
HTTP endpoints; server-side code must derive `firm_id` from authorization. Existing
uploads still go through the validated backend ingestion path. Do not expose direct
PUT uploads until an authenticated completion step enforces catalog restrictions,
size, type and fingerprint validation. No S3 browser CORS is needed for the current flow.

App IAM permits GET/PUT/retention only under this bucket's `firms/*`, with no delete,
list, bucket administration or governance bypass. Tenant isolation is enforced in
the backend; the one shared app role can access all tenants' prefixes. The optional
storage IAM user uses the same policy; `create_app_access_key=false` avoids static
keys on EC2. Enable it only for an explicitly managed external runtime, retrieve
through a secure state process, and rotate/revoke it after migration. Do not print
state or run `terraform show -json` into CI logs when keys exist.

## Cloudflare production portal

The portal already uses `NEXT_PUBLIC_API_URL`. It is compiled into browser code;
Wrangler runtime vars cannot change it after build. Use Node 22:

```sh
cd web
npm ci
NEXT_PUBLIC_API_URL=https://api.example.com npm run build:cloudflare:production
npx opennextjs-cloudflare deploy --env production
```

Set the production Worker's custom domain to `portal.example.com` in Cloudflare.
The production Wrangler environment has a distinct Worker/self-reference and
`workers_dev=false`. Keep the API and portal on sibling HTTPS domains. Backend
`CORS_ORIGINS` and `PORTAL_URL` are set from the Terraform `portal_url` variable;
secure HttpOnly cookies remain backend-owned. Never put secrets in `NEXT_PUBLIC_*`.
Do not use `deploy:demo` for production: it intentionally builds synthetic mocks.
Reset links lead to `/reset-password`; magic links lead to `/sign-in?token=...`.
Disable query-string logging/analytics on all authentication pages at the edge.

## Monthly budget (USD, us-east-2 on-demand, low traffic)

| Item | Approx/month |
| --- | ---: |
| EC2 t4g.micro ($0.0084/hour) | $6.13 |
| One public IPv4 / Elastic IP ($0.005/hour) | $3.65 |
| 20 GB gp3 EBS ($0.08/GB) | $1.60 |
| S3 documents, logs, trail, dumps (a few GB) + requests | $0.10–0.50 |
| CloudTrail first management trail | $0.00 |
| SSM Parameter Store standard SecureStrings | $0.00 |
| Data transfer out (first 100 GB/month free) | $0.00 |
| **Total** | **~$11.50–12.00** |

Excludes tax, domain and Cloudflare. If 1 GB is too tight, `instance_type =
"t4g.small"` adds ~$6. A 1-year Savings Plan roughly halves the instance line.
Budget alerts are notifications, not caps.

## Operations, recovery and remaining release gates

- Set external HTTPS uptime checks and alert ownership; alert on worker queue age,
  failed jobs, Postgres disk/connections, EC2 disk/memory and backup failures.
  Basic EC2 metrics do not include memory/disk; add a CloudWatch agent or equivalent.
  Log rotation is configured for containers; approve retention for DB/CloudTrail logs.
- Patch/rebuild images and the host regularly. Pin the Caddy container to a reviewed
  digest before release. The bootstrap uses `caddy:2` for initial setup. Review
  dependency/security scans, runtime capacity and restore evidence before live use.
- Snapshot before deploy, update the pinned image with Terraform, and plan for a
  replacement host/DNS cutover. DNS TTL and certificate reissue affect downtime.
  Roll back image changes only when compatible with the migrated schema; restore
  snapshots into a new private instance for destructive migration rollback.
- Test credential rotation, synthetic tenant denial, auditor MFA and session
  revocation. Retire expired auth throttle rows/tokens periodically using a reviewed
  maintenance procedure; do not retain auth records indefinitely without a policy.
- `prevent_destroy` is currently off for the lean profile. Never remove retention
  or delete state to force a destroy; dump the DB before any destroy/replace. Retain
  required report versions, backup evidence and trail logs under the approved policy.

## Optional Sentry error monitoring

Sentry free plan -- optional; leave DSNs blank to disable it entirely. No Sentry
account, auth token or source-map upload is required to build or deploy.
Backend settings: `SENTRY_DSN` (blank by default), `SENTRY_ENVIRONMENT` (default
`production`), `SENTRY_TRACES_SAMPLE_RATE` (0 by default; range 0–1). Supply backend
settings through the deployment environment and restart the API. Browser monitoring
uses `NEXT_PUBLIC_SENTRY_DSN`, a public build-time DSN; rebuild the portal after
changing it. Never put a Sentry auth token in public variables.

The browser-only `@sentry/browser` SDK runs through Next.js client instrumentation
and is compatible with OpenNext/Cloudflare Workers without a server SDK or build
plugin. It captures uncaught browser errors; Worker/server-render errors are not
captured. Backend FastAPI exceptions use `sentry-sdk[fastapi]`.

Both scrubbers rebuild events from a strict allowlist: a fixed error label and
numeric stack line/column locations only. Request bodies, cookies, headers, URLs,
users/emails, exception messages, source/locals, breadcrumbs, tags, custom context,
document metadata/content and SAR data are discarded, including unknown fields.
This intentionally limits diagnostic detail and grouping. PII, session tracking,
replay, logs and trace propagation are disabled. Backend transaction events are
always dropped for privacy, even if a nonzero trace sample rate is configured.
Source maps are neither generated for Sentry nor uploaded. Use only synthetic data
when checking delivery; do not add attachments or alternate telemetry transports.
