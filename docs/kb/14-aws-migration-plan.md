# AWS migration plan (outline)

Status: AWS account `095384893776` reinstated 27 Oct 2026 (12:05 AM PT). **No AWS build until Abdullah does root sign-in + MFA and sends the sign-in code.** Region: **us-east-1**. A Codex read-only analysis prompt (docs `docs/aws/00-what-we-have.md`, `docs/aws/01-move-to-aws-plan.md` on branch `docs/aws-plan`) was given to Abdullah to run; results not yet received.

## Account foundations (first)
1. Root sign-in, root MFA, confirm contact/card details match verification documents.
2. IAM Identity Center admin user; no long-lived access keys.
3. Budget alert $10–20/month + cost anomaly detection (repo mentions `kien-monthly-15` $15 budget).
4. CloudTrail (one free management trail). Later GuardDuty/Config as budget allows.
5. Close support case 179288990700916.
6. GitHub OIDC role for CI deploys (least privilege). Tag everything.

## What's already in the repo
`infra/aws` Terraform "lean single-host" profile: one ARM t4g.micro EC2 (Caddy + API + worker + Postgres 16 on localhost), encrypted gp3, only 80/443 open, SSM Session Manager (no SSH), SSM Parameter Store secrets (generated on first boot), S3 documents bucket (versioning, Object Lock enabled, optional KMS), ops bucket (access logs, CloudTrail, daily `pg_dump` 14 days, releases), Elastic IP. Dockerfile already bundles the RDS CA. Doc: `docs/deploy-aws.md`.

## Target options (decide)
| Piece | Cheapest | Step up |
| --- | --- | --- |
| API + worker | Single EC2 (existing Terraform) | ECS Fargate / App Runner |
| Postgres (+pgvector later) | On the EC2 host | RDS Postgres 16 (pgvector supported) |
| Files | S3 + SSE (KMS optional) | — |
| Email | Keep Resend | SES |
| Frontend | Keep Cloudflare Workers | Amplify/CloudFront (not needed) |
| Secrets | SSM Parameter Store | Secrets Manager |
| Logs | CloudWatch basic | + agent, alarms |
Recommendation (inferred, to be confirmed by the plan): start with the existing single-host Terraform, keep Cloudflare frontend and Resend, move to RDS once there are paying clients.

## Migration steps (zero data loss)
1. Apply Terraform in a fresh state path; bring up API on a temporary `sslip.io` host; synthetic smoke test.
2. Copy R2 → S3 (rclone or `aws s3 sync` via S3 API) and verify checksums against `documents.sha256`.
3. Maintenance window: freeze writes, `pg_dump -Fc` on OVH, `pg_restore` on AWS, verify row counts + audit chain (`/auditor/audit-log/verify-chain`).
4. Switch `STORAGE_BACKEND`/bucket settings, point `api.kiensolutions.com` DNS to the Elastic IP (DNS-only), confirm TLS.
5. Verify with both demo logins; keep OVH Kien stack stopped but intact for rollback (≥2 weeks).
**Rollback:** DNS back to OVH + restart old stack; any writes made on AWS must be dumped back first.

## Do not
Touch n8n/Twenty/client portal during teardown; delete OVH data without approval; claim AWS certifications as Kien's.
