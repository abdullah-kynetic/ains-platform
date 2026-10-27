# Kien compliance and AWS control baseline (draft)

## Purpose and status

This is an implementation-grounded control baseline for Kien. It connects the
current application behavior to the proposed AWS environment and identifies the
evidence still needed before production use.

**Status: draft — not an approval, legal opinion, certification, or audit
report.** The repository describes Kien as workflow software supporting an
independent AML test for broker-dealers under FINRA Rule 3310. Kien does not
itself issue a regulatory conclusion. Findings remain drafts until a human
auditor approves them, and report sign-off is an explicit auditor action.

This document does not invent the AML rubric, evidence sufficiency rules,
retention periods, or legal interpretations. Quentin and the responsible
compliance owner must confirm those items before this baseline can be treated as
authoritative.

## Environment model

Testing and production use the same application code and are separate systems:

```text
candidate commit
    -> testing: synthetic data, isolated AWS resources, mocks disabled
    -> approval and evidence review
    -> production: real users and client evidence, same reviewed artifact
```

The proposed AWS backend is:

- **Cloudflare Worker:** web frontend; not an AWS resource. Testing and
  production Workers have separate names and build-time API URLs.
- **EC2:** Caddy HTTPS proxy, FastAPI API, receipt worker, and PostgreSQL 16 on
  localhost in the low-cost profile.
- **S3:** client documents and operational artifacts. Documents use firm-scoped
  keys, encryption, versioning, and Object Lock support.
- **SSM Parameter Store:** runtime secret storage; the instance role retrieves
  parameters. SSM Session Manager is the administration path instead of SSH.
- **CloudTrail:** management-event logging to the operational S3 bucket.
- **IAM/VPC/security group:** instance role, one public subnet, HTTPS/HTTP
  ingress only, and no public PostgreSQL or SSH port.
- **Resend:** email delivery provider, configured outside the repository.

The repository does not prove that these resources are currently deployed. A
Terraform plan and an account read-only review are required before describing
AWS as the live production environment.

## Control matrix

Statuses mean:

- **Implemented:** present in application code or checked-in infrastructure,
  subject to testing and deployment verification.
- **Proposed:** represented in the AWS design but not applied or evidenced.
- **Partial:** some mechanism exists, but an important operational or policy
  control is missing.
- **Unresolved:** an owner decision, legal interpretation, or operational fact is
  still required.

| ID | Control area | Required outcome to confirm | Current Kien control | AWS application/evidence | Status and gap |
| --- | --- | --- | --- | --- | --- |
| C-01 | Governance and independence | The AML test is performed by an appropriately independent auditor and the engagement scope is approved. | Auditor assignment is stored on engagements; findings are drafts; only an assigned auditor can sign off. | Preserve auditor assignment and report-signoff records; retain approval evidence with the engagement. | **Partial.** Independence criteria, approver, and evidence format are not defined in the repository. |
| C-02 | AML methodology | The approved Rule 3310 test rubric, applicability rules, and evidence requirements are controlled and reproducible. | The 34-request YAML catalog is canonical; rubric fields are deliberately empty pending Quentin’s review. | Store the catalog version/snapshot with each engagement; promote the same commit to both environments. | **Unresolved.** The rubric and formal methodology approval are not present. |
| C-03 | Tenant isolation | A firm can access only its own records and an auditor only assigned engagements. | FastAPI applies `firm_id` filters and auditor-assignment checks; denial tests exist. | Keep the API as the only database boundary; isolate testing and production databases and buckets. | **Implemented in code; deployment evidence required.** No database RLS is used. |
| C-04 | Client and auditor identity | Accounts are invite-only, attributable, and deactivated when no longer authorized. | Invite-based accounts, Argon2 password hashes, sessions, password reset, and role checks exist. | Store only server-side secrets in SSM; use HTTPS-only cookies in AWS. | **Partial.** Controlled first-auditor creation and account deactivation are unfinished. |
| C-05 | Auditor MFA | Auditors use a second factor and recovery is controlled. | TOTP enrollment, conditional challenge, hashed one-use recovery codes, and rotation exist. | Test MFA against the production HTTPS domain; record synthetic test evidence. | **Implemented in code; operational test required.** Recovery ownership and incident handling are unresolved. |
| C-06 | Session and credential protection | Sessions expire, can be revoked, and secrets are not exposed to browsers or logs. | Signed session tokens, server-side session rows, revocation, secure-cookie setting, and secret-length checks exist. | `SESSION_SECRET` and database credentials are SSM SecureStrings; no secrets in `NEXT_PUBLIC_*`. | **Partial.** Rotation cadence, emergency revocation, and access review are not defined. |
| C-07 | Document confidentiality | Client evidence is private, encrypted, tenant-scoped, and not stored in ordinary database rows. | Uploads are validated, hashed, and represented by firm-scoped storage metadata; restricted items reject portal uploads. | Private S3 buckets, public-access blocks, TLS-only bucket policies, encryption, versioning, and firm prefixes. | **Partial.** Malware scanning/quarantine and verified restore procedures are missing. |
| C-08 | Restricted/SAR handling | Restricted material is handled only through an approved human process and never sent to a model. | Restricted checklist items are metadata-only in the portal; no model SDK or inference call is in `app/`. | Do not create a restricted-material bucket or pipeline without an approved design; keep testing synthetic. | **Implemented boundary; handling procedure unresolved.** |
| C-09 | Upload integrity and neutral feedback | The system rejects unsafe uploads and gives clients document-level feedback, not audit findings. | Extension/signature/size checks, SHA-256 fingerprints, 100 MB limit, receipts, and fixed neutral feedback codes exist. | S3 receipt objects use server-side encryption; worker verifies stored receipt metadata. | **Implemented in code; operational evidence required.** Malware and stronger Office validation remain gaps. |
| C-10 | Audit trail | Important actions are attributable, time-stamped, tamper-evident, and reviewable. | Per-firm SHA-256 hash chains, sequence locking, ORM guards, and PostgreSQL mutation triggers exist. | CloudTrail records AWS management events; retain application audit exports according to policy. | **Partial.** External audit-chain checkpoints and privileged-database threat controls are not implemented. |
| C-11 | Human review and report approval | Automated receipt checks cannot become audit findings; a human approves findings and the final report. | Worker checks storage receipts only; auditor manually accepts/edits/rejects findings; sign-off records report hash and attestation. | Keep report artifacts versioned; do not describe hash attestation as a cryptographic document signature. | **Implemented in code; final signing/delivery procedure unresolved.** |
| C-12 | Backup and restoration | Data can be restored within an approved recovery objective and restoration is periodically proven. | Repository has no production backup service outside the AWS profile. | Daily `pg_dump` to the operational S3 bucket; S3 versioning; SSM access. | **Partial.** No point-in-time recovery, failover, restore schedule, RTO/RPO, or drill evidence. RDS should be evaluated for production. |
| C-13 | Change management and promotion | Production runs only reviewed, tested, traceable artifacts and can be rolled back. | CI and unit/integration/browser tests exist; testing and production deployment commands now separate builds. | Use separate Terraform state; promote the same image/commit; retain prior image, EIP, and verified database dump. | **Partial.** Human approval record, release owner, and signed artifact process are not defined. |
| C-14 | Monitoring and alerting | Failures affecting security, availability, backups, or queues are detected and assigned. | Health endpoint, optional privacy-scrubbed Sentry, and worker job states exist. | CloudTrail and container logs exist in the design. | **Partial.** Alerts for queue age, backup failure, disk, memory, database, and HTTPS availability are not provisioned. |
| C-15 | Retention and deletion | Documents, reports, logs, tokens, and database records follow approved retention and deletion rules. | Storage retention is configurable; many table retention periods are explicitly unresolved. | S3 lifecycle rules exist for old versions and operational artifacts; Object Lock can protect final reports. | **Unresolved.** No approved schedule, legal hold, deletion workflow, export process, or owner exists. |
| C-16 | Access administration | Administrative access is least-privilege, reviewed, logged, and removed promptly. | Application roles and engagement assignment checks exist. | EC2 instance role avoids static AWS keys; SSM is the admin path; app IAM is scoped to document prefixes and backups. | **Partial.** AWS human-role design, MFA, access reviews, break-glass access, and separation of duties are not documented. |
| C-17 | Network and transport security | Public traffic is encrypted and databases are not directly internet-accessible. | Secure cookie option and strict CORS configuration exist. | Caddy terminates HTTPS; security group exposes 80/443 only; PostgreSQL/API bind to localhost. | **Implemented in proposed profile; verification required.** WAF, rate limiting, and account lockout remain gaps. |
| C-18 | Vendor and data location | External providers, regions, subprocessors, and data flows are approved. | Resend, Cloudflare, S3-compatible storage, optional Egnyte, and optional Sentry are explicit integration boundaries. | Proposed AWS region is `us-east-1`; Cloudflare and Resend remain external. | **Unresolved.** Contracts, residency, subprocessors, and vendor reviews are not in the repository. |
| C-19 | Software assurance | Changes are tested, dependencies reviewed, and deployment configuration is reproducible. | Lockfiles, CI, Ruff, pytest, ESLint, TypeScript, and browser tests exist. | Terraform provider is locked; production should use reviewed immutable ARM64 images. | **Partial.** Dependency-update policy, image scanning, Terraform validation in CI, and release attestations are missing. |
| C-20 | Incident response and continuity | Security incidents, suspected cross-tenant access, lost credentials, and provider outages have documented response steps. | Application errors avoid logging secrets/document contents; audit events provide investigation context. | SSM enables administration; CloudTrail and S3 logs provide AWS evidence. | **Unresolved.** No incident plan, notification matrix, forensic procedure, or client communication process is documented. |

## Evidence package required for approval

Before production data is accepted, collect and retain (without putting secrets
or client document contents in Git):

1. Approved AML methodology, rubric, applicability rules, and evidence list.
2. Named owners for auditor independence, security, AWS operations, retention,
   incident response, and release approval.
3. Reviewed Terraform plan for testing and production, including account, region,
   resource names, bucket settings, IAM policies, and replacements.
4. AWS configuration evidence for S3 public-access blocking, encryption,
   versioning/Object Lock, security groups, CloudTrail, SSM, and instance-role
   permissions.
5. Synthetic end-to-end test evidence covering invitations, passwords, MFA,
   tenant denial, upload rejection, neutral feedback, worker receipts, report
   draft generation, and auditor sign-off.
6. A successful backup restore into an isolated scratch database, with measured
   recovery time and documented data-loss window.
7. Production-like staging evidence proving the same artifact is promoted without
   rebuilding or changing application logic.
8. Access review, dependency/image review, alert test, secret-rotation test, and
   rollback test records.

## Decisions that must be approved

- Is Kien supporting an auditor’s independent AML test only, or is any additional
  regulated service in scope?
- What exact Rule 3310 requirements and approved rubric does Quentin sign off?
- What are the required retention, legal-hold, deletion, export, RTO, and RPO
  periods for each data class?
- Is the one-host PostgreSQL design acceptable for production, or is RDS required?
- Who can create, deactivate, reassign, and review auditors and client users?
- Which AWS and external-provider regions, subprocessors, and data flows are
  approved?
- What monitoring alerts are mandatory, who receives them, and what is the
  escalation clock?
- What incident-notification and client-communication obligations apply?
- What evidence makes a release approved, and who can promote testing to
  production?

Until these decisions are answered and the evidence package is reviewed, this
baseline should be treated as an engineering readiness document only.
