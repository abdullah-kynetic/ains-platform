# Kien AWS environments

This directory describes the AWS backend for the same Kien application in two
isolated environments:

- **testing**: synthetic users and files only; used to verify a candidate build.
- **production**: real users and client evidence; receives only the exact build
  that passed testing.

The environments must use different Terraform state files, instance names,
S3 buckets, SSM parameter prefixes, domains, and databases. Never point testing
at production resources, and never copy production documents into testing.

## What this profile runs

One ARM64 EC2 host runs Caddy (HTTPS), the FastAPI API, the receipt worker, and
PostgreSQL 16 on localhost. S3 stores documents and operational artifacts;
Parameter Store holds runtime secrets; SSM Session Manager is the administration
path; CloudTrail records management events. The Cloudflare Worker remains the
web frontend and is built from the same commit with environment-specific public
API configuration.

This is the lowest-cost profile, not a high-availability design. The database
is on the host, so the daily dump is the recovery boundary. Move production to
RDS before volume or recovery requirements justify the additional cost.

## Safe configuration workflow

1. Create a git archive from the candidate commit. Do not include `.env` files,
   credentials, real client files, or generated build artifacts.
2. Copy the appropriate example to an untracked local file and replace only
   placeholders: `terraform.testing.tfvars.example` or
   `terraform.production.tfvars.example`.
3. Use a new local state path per account and environment. Never reuse testing
   state for production.
4. Run `terraform fmt -check`, `terraform init`, and `terraform plan`. Review
   the plan for bucket names, region, domain, environment tag, and replacements.
5. Apply only after review and an explicit change window. This repository does
   not apply AWS changes automatically.
6. Verify health, login/MFA, tenant isolation, synthetic upload, worker receipt,
   email (where configured), backup creation, and a restore into a scratch DB.
7. Promote the same immutable application image or git commit to production.
   Do not rebuild from a different source between testing and production.

Example state separation (paths are illustrative):

```sh
terraform init -backend-config=path=/secure/kien-state/<account-id>/testing.tfstate
terraform plan -var-file=/secure/kien-state/<account-id>/testing.tfvars
```

Use a separate `production.tfstate` and `production.tfvars` for production.
Keep state outside the repository and protect it as sensitive operational data.

## Rollback boundary

Before replacing a host or changing migrations, create and verify a PostgreSQL
dump. Keep the previous application image and the existing EIP. If the new
build fails, restore the previous image and restart the services. If a schema
change is not backward-compatible, restore the database dump into a replacement
host and cut DNS back only after verifying the restored copy. Do not destroy an
S3 bucket or overwrite locked document versions as a rollback technique.

The low-cost profile does not provide point-in-time recovery or automatic
failover. Those are explicit reasons to adopt RDS and a more redundant design.
