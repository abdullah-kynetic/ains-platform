# Accepted security risks

Only the explicitly recorded findings below are suppressed. A finding may only be accepted here
with its scanner and finding ID, affected path/package, reason, owner and expiry
(YYYY-MM-DD). Expired entries must fail review. The policy validates these records and generates temporary scanner configuration
or filters only exact approved rule/file metadata from valid scanner reports;
expired, malformed or unsupported records fail closed. Do not add tool-native ignore files or inline suppressions to bypass CI.

| ID | Reason | Owner | Expiry | Compensating controls |
| --- | --- | --- | --- | --- |
| CodeQL unavailable | Private repository code scanning requires paid GitHub Code Security; the plan requires free tools. This is a tool coverage exception, not a finding suppression. | Abdullah | 2027-02-09 | Semgrep CE, Bandit, zizmor, dependency, container and secret scans |

Security runs every scanner as a separate matrix job, with fail-fast disabled.
Any nonzero exit fails its job, including unavailable registries/rules or tool errors.
Dependency auditing is conservative: pip-audit also fails on lower-severity findings.
Gitleaks flags any secret; TruffleHog flags verified secrets only. Trivy gates High
and Critical. Semgrep and Bandit enforce the plan's configured rules/thresholds.

Artifacts contain scanner names, exit statuses and allowlisted finding metadata
(IDs, paths/packages and severities). Raw output is captured in a
private temporary directory and removed on exit, because verified-secret and
filesystem reports can contain secret values. Investigate findings in a secure
local environment; never paste raw scanner logs into PRs or upload unredacted reports.

## Owner-approved finding exceptions

The JSON block is the only machine-readable exception source. All entries
expire after 90 days. Fingerprints apply only to the exact historical findings;
no git history is changed. No matched values are recorded here.

```json
[
  {
    "scanner": "zizmor",
    "finding": "dangerous-triggers",
    "scope": ".github/workflows/image.yml",
    "reason": "Owner accepted: publication is restricted to trusted same-repository main pushes or manual main dispatch; PR code never runs with package write.",
    "owner": "Abdullah via Slave Kien",
    "approved": "2026-11-09",
    "expires": "2027-02-07"
  },
  {
    "scanner": "gitleaks",
    "finding": "generic-api-key",
    "scope": "tests/test_auditor_assignment.py",
    "fingerprint": "51be7fac893258ac8f2ffc36dd7c364d778f65ec:tests/test_auditor_assignment.py:generic-api-key:27",
    "reason": "Fixed TOTP secret for a synthetic second auditor created through the isolated database fixture, using example.test; not an external credential.",
    "owner": "Abdullah via Slave Kien",
    "approved": "2026-11-09",
    "expires": "2027-02-07"
  },
  {
    "scanner": "gitleaks",
    "finding": "generic-api-key",
    "scope": "web/src/lib/invoice-api.ts",
    "fingerprint": "57b52e5fdaf600c91c135a8469929005daa191dd:web/src/lib/invoice-api.ts:generic-api-key:61",
    "reason": "Synthetic invoice localStorage namespace; a browser storage key, not an API credential.",
    "owner": "Abdullah via Slave Kien",
    "approved": "2026-11-09",
    "expires": "2027-02-07"
  },
  {
    "scanner": "gitleaks",
    "finding": "generic-api-key",
    "scope": "web/e2e/auditor.spec.ts",
    "fingerprint": "f8f40ffc09048724429bec5ae66189dcd5ce3dff:web/e2e/auditor.spec.ts:generic-api-key:22",
    "reason": "Synthetic localStorage namespace used to seed evidence in a browser test, not an API credential.",
    "owner": "Abdullah via Slave Kien",
    "approved": "2026-11-09",
    "expires": "2027-02-07"
  },
  {
    "owner": "Abdullah via Slave Kien",
    "approved": "2026-11-09",
    "expires": "2027-02-07",
    "review": "Stage 2 security audit",
    "scanner": "semgrep",
    "finding": "python.lang.security.audit.logging.logger-credential-leak.python-logger-credential-disclosure",
    "scope": "ai_adapter/client.py",
    "reason": "Owner accepted until Stage 2/3: ai_adapter is frozen and disabled; no adapter edits or model runs are authorized. Stage 2 must audit logging before enabling it."
  },
  {
    "owner": "Abdullah via Slave Kien",
    "approved": "2026-11-09",
    "expires": "2027-02-07",
    "review": "Stage 2 security audit",
    "scanner": "semgrep",
    "finding": "javascript.browser.security.wildcard-postmessage-configuration.wildcard-postmessage-configuration",
    "scope": ".agents/skills/impeccable/scripts/live-browser.js",
    "reason": "Owner accepted: local agent tooling is never shipped with the product. Stage 2 must review cross-window messaging before this tooling is enabled beyond its existing local context."
  },
  {
    "owner": "Abdullah via Slave Kien",
    "approved": "2026-11-09",
    "expires": "2027-02-07",
    "review": "Stage 2 security audit",
    "scanner": "trivy-fs",
    "finding": "AWS-0015",
    "scope": "infra/aws/main.tf",
    "reason": "Owner accepted: legacy AWS infrastructure is not used by the single VPS environment and is not deployed. Stage 2 must review and remediate this rule before any AWS use."
  },
  {
    "owner": "Abdullah via Slave Kien",
    "approved": "2026-11-09",
    "expires": "2027-02-07",
    "review": "Stage 2 security audit",
    "scanner": "trivy-fs",
    "finding": "AWS-0086",
    "scope": "infra/aws/main.tf",
    "reason": "Owner accepted: legacy AWS infrastructure is not used by the single VPS environment and is not deployed. Stage 2 must review and remediate this rule before any AWS use."
  },
  {
    "owner": "Abdullah via Slave Kien",
    "approved": "2026-11-09",
    "expires": "2027-02-07",
    "review": "Stage 2 security audit",
    "scanner": "trivy-fs",
    "finding": "AWS-0087",
    "scope": "infra/aws/main.tf",
    "reason": "Owner accepted: legacy AWS infrastructure is not used by the single VPS environment and is not deployed. Stage 2 must review and remediate this rule before any AWS use."
  },
  {
    "owner": "Abdullah via Slave Kien",
    "approved": "2026-11-09",
    "expires": "2027-02-07",
    "review": "Stage 2 security audit",
    "scanner": "trivy-fs",
    "finding": "AWS-0091",
    "scope": "infra/aws/main.tf",
    "reason": "Owner accepted: legacy AWS infrastructure is not used by the single VPS environment and is not deployed. Stage 2 must review and remediate this rule before any AWS use."
  },
  {
    "owner": "Abdullah via Slave Kien",
    "approved": "2026-11-09",
    "expires": "2027-02-07",
    "review": "Stage 2 security audit",
    "scanner": "trivy-fs",
    "finding": "AWS-0093",
    "scope": "infra/aws/main.tf",
    "reason": "Owner accepted: legacy AWS infrastructure is not used by the single VPS environment and is not deployed. Stage 2 must review and remediate this rule before any AWS use."
  },
  {
    "owner": "Abdullah via Slave Kien",
    "approved": "2026-11-09",
    "expires": "2027-02-07",
    "review": "Stage 2 security audit",
    "scanner": "trivy-fs",
    "finding": "AWS-0104",
    "scope": "infra/aws/main.tf",
    "reason": "Owner accepted: legacy AWS infrastructure is not used by the single VPS environment and is not deployed. Stage 2 must review and remediate this rule before any AWS use."
  },
  {
    "owner": "Abdullah via Slave Kien",
    "approved": "2026-11-09",
    "expires": "2027-02-07",
    "review": "Stage 2 security audit",
    "scanner": "trivy-fs",
    "finding": "AWS-0132",
    "scope": "infra/aws/main.tf",
    "reason": "Owner accepted: legacy AWS infrastructure is not used by the single VPS environment and is not deployed. Stage 2 must review and remediate this rule before any AWS use."
  }
]
```

The owner also approved exact Semgrep rule/file and legacy AWS misconfiguration
exceptions, all flagged for the Stage 2 security audit. Scanners still run in full.
Report filtering never accepts secret findings, unrelated rules/files, scanner
errors, malformed reports or non-finding exit codes. No container CVE is suppressed;
the pinned Alpine application image scans clean.
