# Accepted security risks

No scanner finding is currently suppressed. A finding may only be accepted here
with its scanner and finding ID, affected path/package, reason, owner and expiry
(YYYY-MM-DD). Expired entries must fail review. Adding an entry alone does not
silence a scanner: any implementation of an exception must validate this record
and expiry. Do not add tool-native ignore files or inline suppressions to bypass CI.

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
