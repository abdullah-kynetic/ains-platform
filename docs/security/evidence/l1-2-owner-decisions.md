# L1-2 follow-up: owner decisions and remediation

Owner direction received 2026-11-09 (America/Los_Angeles).
Base main `35fc84e` merged into #97 with real merge commit `37d255b`.
No history rewrite or force-push.

## Approved exceptions

The owner approved the image workflow_run risk for 90 days, because only trusted
same-repository main pushes/manual main dispatch can publish; PR code never gets
package-write access. The policy generates a temporary zizmor ignore for the
workflow_run line only. The image source is additionally verified as an ancestor
of canonical main before checkout, registry login or build.

Three Gitleaks historical matches were inspected without printing matched values:

- `51be7fac893258ac8f2ffc36dd7c364d778f65ec`, tests/test_auditor_assignment.py:27:
  fixed TOTP secret for an isolated second-auditor test fixture, synthetic
  example.test identity, no service credential.
- `57b52e5fdaf600c91c135a8469929005daa191dd`, web/src/lib/invoice-api.ts:61:
  synthetic localStorage namespace, not an authentication credential.
- `f8f40ffc09048724429bec5ae66189dcd5ce3dff`, web/e2e/auditor.spec.ts:22:
  synthetic localStorage namespace for browser evidence seeding.

All four exact exceptions are recorded in accepted-risks.md with reasons, owner,
approval date and expiry 2027-02-07 (90 days). Expired, malformed, duplicate or
unsupported entries fail closed. No native ignore file is committed; generated
configuration exists only in the scanner's private temporary directory.
Local and hosted Gitleaks and zizmor passed with these exceptions.

## Findings remediated in owned paths

- Semgrep's workflow-run checkout finding: canonical main is checked out first;
  the requested 40-character SHA must be an ancestor of origin/main before use.
  A real temporary-git-repository test rejects untrusted commits and ref injection.
- Semgrep's uv cooldown finding: exclude-newer = 7 days; lock options updated
  without changing dependency versions. #37 had merged before this edit.
- Trivy generated-dependency fixtures: Security no longer runs uv sync/npm ci,
  nor uv run for the stdlib policy. The scanner jobs need source/lockfiles only.
  Frozen application installs remain enforced by CI. No tracked source is excluded.
- Debian base image: 49 High/Critical findings included system packages with no
  reported fixed version. Replaced it with the official Python 3.12 Alpine base,
  pinned by digest. Existing production dependencies install from the same lock.
  Optional public CA bundle build-secret mounts support cloud TLS interception;
  no CA or credential is copied into the image.
- Added a required non-root/read-only runtime smoke check before image scanning:
  API health via ASGI, worker import, PostgreSQL driver, in-memory SQLite models,
  synthetic DOCX and PDF generation.

Actual local commands passed:

- `BUILDX_CONFIG=/tmp/kien-buildx docker build --secret id=proxy_ca,src=/etc/ssl/certs/ca-certificates.crt -t kien-api:ci .`
- `docker run --rm --read-only --cap-drop ALL --security-opt no-new-privileges --tmpfs /tmp -v "$PWD/.github/scripts/image-smoke.py:/app/smoke.py:ro" --entrypoint python kien-api:ci /app/smoke.py`
- `docker save -o /tmp/kien-api-alpine.tar kien-api:ci`
- `TRIVY_CACHE_DIR=/tmp/kien-trivy-cache /tmp/kien-bin/trivy image --db-repository ghcr.io/aquasecurity/trivy-db:2 --input /tmp/kien-api-alpine.tar --severity HIGH,CRITICAL --exit-code 1 --format json`
  Exit 0, zero High/Critical findings across four application-image scan targets.
  The binary was copied from the same official Trivy 0.69.3 scanner image. Its
  default database mirror was blocked; the official GHCR database source worked.

## Remaining cross-owner findings

Hosted annotations from run 42725852034 identify these unsuppressed findings:

- Semgrep: logger-credential-disclosure in ai_adapter/client.py; three
  wildcard-postmessage-configuration findings in
  .agents/skills/impeccable/scripts/live-browser.js.
- Trivy: AWS-0015, AWS-0086, AWS-0087, AWS-0091, AWS-0093, AWS-0104 and AWS-0132
  in infra/aws/main.tf (12 findings; AWS-0104 is Critical).

BLOCKED(owner): These paths are outside Lane 1 ownership, and ai_adapter is
explicitly frozen. Requested routing to Lane 2 or owner-approved scoped exceptions.
No changes or suppressions have been made for these findings.

BLOCKED(owner): Image digest from run 42721702820 remains unretrievable. Logs and
artifact downloads redirect to domains blocked by the cloud policy; package reads
are unauthorized. No digest guessed; no RELEASES row fabricated; no deployment.

L1-3 follows only after #97 is fully green and merged, per the owner's latest
sequence. Its revised memory budget is PostgreSQL 768M, ClamAV approximately 1.2G
with ConcurrentDatabaseReload=no, API 512M, worker 384M, Caddy 128M, and disabled
ai-adapter 256M. No server access is needed or authorized.

## Superseding owner decision: scoped Stage 2 exceptions

The owner subsequently instructed Lane 1 not to route these to Lane 2. The frozen
adapter, local agent tooling and legacy AWS findings above are now explicitly
accepted by exact rule ID and file until 2027-02-07, each flagged for the Stage 2
security audit. Their records are in accepted-risks.md. No source in these paths
was edited. The earlier cross-owner BLOCKED entry is superseded by this decision.

Semgrep and Trivy still scan all tracked source. The policy removes only exact
approved rule/file matches from valid finding reports. It never clears runtime
exit codes, missing/malformed reports, report errors, unrelated rules/files,
Trivy secret findings or vulnerability findings. Accepted metadata and expiry
remain visible in the sanitized artifacts. All expiry checks run before scanning.
TruffleHog's verified-secret gate remains unchanged and has no exceptions.

Hosted run 42726926633 proved the Alpine remediation: trivy-image passed, along
with Gitleaks, zizmor, pip-audit, npm, TruffleHog and Bandit (seven green jobs).
The only failures were the now owner-approved Semgrep/AWS findings. A final
hosted run with their exact report filtering is required before merging #97.

Independent code verification at a702571: PASS, 69 targeted tests, Ruff and
policy/shell checks passed; hardened local image runtime smoke passed again.
Full backend checkpoint: 433 passed, 11 skipped, one dependency warning. Web lint,
typecheck, 28 unit tests and both builds passed. Real-backend browser suite: 8
passed. Mock suite: 80 passed, 2 cloud-proxy tenant-host failures (same Domain
forbidden evidence as the earlier checkpoint).
