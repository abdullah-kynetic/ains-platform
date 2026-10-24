# AWS deployment runbook

This is a low-volume, single-region deployment baseline, not a certification or a
high-availability service. No AWS resources were created while preparing it.
Quinton must approve the control evidence, retention policy and release before client use.
Use synthetic documents for every deployment smoke test.

## Design and tradeoffs

`infra/aws` deploys an ARM64 EC2 t4g.micro running the API, receipt worker and Caddy
HTTPS proxy, plus encrypted **private** single-AZ RDS PostgreSQL db.t4g.micro. Two
private database subnets have no internet route. Only the app security group can
connect on 5432. RDS forces TLS, backs up automatically for seven days, and has
snapshot/deletion protection. The app instance has encrypted EBS, IMDSv2, no SSH
port and SSM administration. There is no NAT gateway or load balancer charge.

Lightsail nano/micro containers are attractive at roughly $7/$10 per month with
simple managed HTTPS and predictable pricing. They cannot directly reach this
private RDS VPC. Lightsail instance VPC peering does not make a Lightsail container
service a VPC-attached workload. Making RDS public is unacceptable here. A Lightsail
managed database changes the requested RDS service and backup/networking controls.
Therefore the runnable Terraform deliberately selects EC2 instead of provisioning an
unusable Lightsail container service. App Runner with a VPC connector is workable,
but outbound Resend access needs an egress design, typically a NAT gateway
whose hourly cost exceeds this application's compute cost. EC2 needs OS patching
and more operator work; managed services become preferable as usage grows.

There is one API/worker host and no automatic failover. A host replacement or
migration interrupts service. Monitor it and test restores; move to redundant
compute and multi-AZ RDS when the availability requirement justifies the expense.
AWS resources alone do not prove due-diligence acceptance.

## What Abdullah must provide

- AWS account with billing enabled, root MFA, recovery contacts, target region
  (default `us-east-1`), and a budget notification address. Confirm credit eligibility
  and expiry in Billing; production should use a paid account plan.
- A deployment IAM identity (prefer short-lived SSO/role credentials). If a deploy
  IAM user/access key is required, supply it through your local AWS profile, never
  Terraform inputs, source code or chat. Its reviewed policy needs this deployment's
  VPC/subnet/routes/security groups, EC2/EIP/EBS, RDS/subnet/parameter groups, S3,
  CloudTrail and IAM lifecycle permissions, `iam:PassRole` restricted to this EC2
  role, plus provider read/list/tag permissions. A deploy identity is separate from
  the app storage user; do not attach app credentials to Terraform administration.
- Domain and DNS access: `api.example.com` for AWS and `portal.example.com` for
  Cloudflare, under the same registrable domain for SameSite session cookies.
- Cloudflare account/zone and a deployment token restricted to the target Worker/zone.
- Resend account, a sending-only API key restricted to the verified domain, sender
  address, and DNS access for Resend's exact SPF and DKIM records. Add DMARC at
  `_dmarc` (begin with monitored `p=none`, then enforce after validating alignment).
  Do not publish multiple SPF records for one hostname; merge as needed.
- ARM64 backend image in a public registry, pinned by SHA256 digest. The image
  contains code/catalog/templates only, never environment files or documents.
- Three existing Secrets Manager secret ARNs: SESSION_SECRET (random, at least
  32 bytes), RESEND_API_KEY, DATABASE_URL. Create values using the console's secure
  editor. DATABASE_URL can initially be a placeholder until RDS exists.
  No Egnyte account or credentials are needed for the primary S3 deployment.
  Use the default Secrets Manager encryption key; a customer key requires an
  additional narrowly scoped `kms:Decrypt` policy for the instance role.
- Quinton's choice of final-report retention days and GOVERNANCE/COMPLIANCE mode.
  COMPLIANCE retention cannot be shortened even by the account root. No application
  action automatically finalizes a finding or signs a report.

## Local release checks and image

```sh
uv sync --frozen
uv run ruff check .
uv run pytest
uv run python scripts/evaluate_synthetic.py
export PATH="$HOME/.local/node22/bin:$PATH"
(cd web && npm ci && npm run lint && npm run build && npm run typecheck)
(cd web && npx playwright test)
docker buildx build --platform linux/arm64 -t ghcr.io/YOUR_ORG/ains-platform:RELEASE --push .
```

Record the resulting digest in `app_image`. The Python 3.12 slim image runs as a
non-root user; its entrypoint runs `alembic upgrade head` and starts uvicorn only
if migrations succeed. The worker overrides the entrypoint to avoid simultaneous
migration runs. Apply migrations with a single API instance; take a DB snapshot
before schema changes. The RDS trust bundle is installed in the image for TLS
certificate verification. Rebuild regularly for base-image and trust-store updates.

## Provision (operator executes, not the coding agent)

1. Install Terraform >=1.7 and AWS CLI v2. Authenticate your deployment profile.
   Set a monthly budget around $60 with warnings at 50/80/100 percent. Budget alerts
   are notifications, not spending caps. Create the three Secrets Manager entries
   above; put only their ARNs into `secret_arns`.
2. Copy `infra/aws/terraform.tfvars.example` to `infra/aws/terraform.tfvars`. Fill
   in your unique bucket name, domains, sender, image digest and secret ARNs.
   Terraform never fetches secret values. RDS manages its master password in a
   separate Secrets Manager secret. Default SSE is AES256; choosing `aws:kms`
   creates a rotating customer key and grants only data-key/decrypt operations.
3. Secure Terraform state before applying: use an access-controlled encrypted S3
   remote backend with locking (`use_lockfile = true`), or encrypted local storage
   for the initial bootstrap. The state backend must exist separately from this
   stack. Keep state, plans, tfvars and AWS credentials out of git. If enabling
   `create_app_access_key`, its secret **will be in Terraform state**.

   ```sh
   cd infra/aws
   terraform init
   terraform fmt -check
   terraform validate
   terraform plan -out=release.tfplan
   terraform apply release.tfplan
   terraform output
   ```

4. Create the API DNS A record pointing at `api_ip` (DNS-only while Caddy obtains
   its certificate). Ports 80/443 serve redirects/HTTPS; port 8000 is published
   only on host loopback. No SSH access is opened. Bootstrap may retry while the
   DATABASE_URL placeholder is present; this is expected and not a ready service.
5. Connect to the instance using SSM Session Manager (`instance_id` output).
   Use an operator-controlled session to initialize a separate database login
   `ains_app`, own the `ains` database/schema and grant it the privileges needed by
   Alembic. Retrieve the RDS-managed master credential only in your secure operator
   session, never into Terraform or logs. The app role deliberately cannot read
   that administrator secret. Keep the master identity for administration only.
6. Replace the DATABASE_URL secret value with the application login URL:
   `postgresql+psycopg://ains_app:URL_ENCODED_PASSWORD@RDS_HOST:5432/ains?sslmode=verify-full&sslrootcert=/usr/local/share/rds-ca.pem`.
   Percent-encode special characters in the password. Use the RDS hostname rather
   than an IP so certificate hostname validation succeeds. Do not print the URL.
   On the instance, run `sudo systemctl restart ains` then
   `sudo systemctl restart ains-worker`. Boot/restart fetches secret values into
   a root-only `/etc/ains/runtime.env` file; no secret appears in user-data or
   Terraform. Restart both services after any secret rotation.
7. Verify `https://api.example.com/health`; liveness alone does not verify the DB,
   worker or email. Review service state through SSM (`systemctl status ains
   ains-worker ains-proxy`) without dumping environment files. Use the existing
   synthetic seed/bootstrap procedure only in an isolated staging database;
   provision production auditor identities through a controlled operator process,
   then complete mandatory auditor MFA. Do not load demo users into production.
8. Check Resend DNS verification, then send invitations, magic links and resets to
   controlled synthetic test accounts. Invitation preview stays disabled. Verify
   the password-reset generic response for unknown addresses and token replay
   denial. Reset requests are limited to 3/email/hour and 20/IP/hour in Postgres;
   the proxy forwards trusted client IPs and the backend port is not public.
9. Upload a synthetic accepted document and confirm its receipt worker finishes.
   Check S3 encryption, version ID, server-access-log delivery (delayed), and
   CloudTrail management and document object events. Test cross-firm denial.
   Confirm RDS backup retention and perform a restore into a separate isolated DB.

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

## Monthly budget (USD, planning estimate)

Illustrative `us-east-1`, 730 hours, on-demand, low traffic, 10 GB documents. Confirm
live AWS Calculator prices for the account/region before deployment. This estimates
about **$46/month including a roughly $12 reserve**; the lean resource bill is closer
to $34. It excludes tax, domain registration, paid support, heavy egress, extra DB
snapshots and burst CPU credits. Single-AZ savings trade away availability.

| Item | Approx/month |
| --- | ---: |
| EC2 t4g.micro (~$0.0084/hour) | $6.13 |
| One public IPv4 (~$0.005/hour) | $3.65 |
| 12 GB gp3 EBS (~$0.08/GB) | $0.96 |
| RDS PostgreSQL db.t4g.micro (~$0.016/hour) | $11.68 |
| RDS 20 GB gp3 (~$0.115/GB); 7-day backups within included allowance | $2.30 |
| Secrets Manager: 3 app secrets + RDS master, low API volume | $1.65 |
| S3 documents/versions, logs, CloudTrail storage and light requests | $1.00 |
| CloudTrail first management trail + light S3 data events | $0.10 |
| CloudWatch logs/monitoring allowance | $1.50 |
| Cloudflare Workers paid base (or $0 if free limits suffice) | $5.00 |
| Resend within free tier; DNS on existing zone | $0.00 |
| Usage reserve | $12.00 |
| **Budget total** | **$46.97** |

This budget assumes S3 only: $0 for Egnyte subscriptions, credentials or secret
storage. Optional customer KMS encryption adds roughly $1/key/month plus API calls.
There is no NAT, ALB or Route 53 hosted zone in this template. S3 versions/logs accumulate: review storage monthly, and
approve lifecycle/archival rules consistent with retention before enabling them.

New eligible AWS accounts currently receive $100 immediately and can earn another
$100. That can cover most AWS costs for the initial months, not a perpetual free
production environment; credits do not cover Cloudflare or domain fees. Check service
eligibility/expiry and upgrade account plan before using the free-plan expiry as an
availability risk. Sources: [AWS Free Tier](https://aws.amazon.com/free/),
[EC2 pricing](https://aws.amazon.com/ec2/pricing/on-demand/),
[RDS PostgreSQL pricing](https://aws.amazon.com/rds/postgresql/pricing/),
[S3 Object Lock](https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lock.html),
[Resend HTTP API](https://resend.com/docs/api-reference/emails/send-email).

## Operations, recovery and remaining release gates

- Set external HTTPS uptime checks and alert ownership; alert on worker queue age,
  failed jobs, RDS CPU/storage/connections, EC2 disk/memory and backup failures.
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
- RDS deletion protection and S3 `prevent_destroy` deliberately block casual
  teardown. Never remove retention or delete state to force a destroy. Retain
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
