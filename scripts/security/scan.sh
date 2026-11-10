#!/usr/bin/env bash
# Export only allowlisted finding metadata; raw scanner output may contain secrets.
set -euo pipefail
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
scanner=${1:?Usage: scan.sh <scanner>}
case "$scanner" in
  pip-audit|npm|gitleaks|trufflehog|trivy-fs|trivy-image|semgrep|bandit|zizmor) ;;
  *) echo 'Unknown scanner' >&2; exit 2 ;;
esac
mkdir -p security-reports
umask 077
scratch=$(mktemp -d)
trap 'rm -rf "$scratch"' EXIT
scan() {
  case "$scanner" in
    pip-audit)
      uv export --frozen --no-dev --format requirements-txt > "$scratch/req.txt"
      uvx pip-audit -r "$scratch/req.txt" --strict --format json > "$scratch/findings.json" ;;
    npm) (cd web && npm audit --omit=dev --audit-level=high --json > "$scratch/findings.json") ;;
    gitleaks)
      docker run --rm -v "$PWD:/repo:ro" -v "$scratch:/reports" -w /repo \
        ghcr.io/gitleaks/gitleaks:v8.30.0 git --redact --report-format json --report-path /reports/findings.json --exit-code 1 . ;;
    trufflehog)
      docker run --rm -v "$PWD:/repo:ro" -w /repo \
        trufflesecurity/trufflehog:3.93.3 git file://. --only-verified --fail --json > "$scratch/findings.json" ;;
    trivy-fs)
      docker run --rm -v "$PWD:/repo:ro" -w /repo aquasec/trivy:0.69.3 \
        fs --scanners vuln,secret,misconfig --severity HIGH,CRITICAL --exit-code 1 --format json . > "$scratch/findings.json" ;;
    trivy-image)
      docker build -t kien-api:ci .
      docker save -o "$scratch/image.tar" kien-api:ci
      docker run --rm -v "$scratch:/scan:ro" aquasec/trivy:0.69.3 \
        image --input /scan/image.tar --severity HIGH,CRITICAL --exit-code 1 --format json > "$scratch/findings.json" ;;
    semgrep)
      uvx semgrep scan --config p/python --config p/typescript \
        --config p/owasp-top-ten --config p/secrets --error --json > "$scratch/findings.json" ;;
    bandit) uvx bandit -r app ai_adapter -ll -ii -f json > "$scratch/findings.json" ;;
    zizmor) uvx zizmor --format json .github/workflows > "$scratch/findings.json" ;;
  esac
}
# Keep errexit active inside scan: an export/build failure must not be hidden
# by a successful later command. Do not invoke scan as an `if` condition.
set +e
(set -e; scan) > "$scratch/raw.log" 2>&1
result=$?
set -e
printf 'Scanner: %s\nExit status: %s\n' "$scanner" "$result" \
  > "security-reports/$scanner.txt"
python3 "$script_dir/report.py" "$scanner" "$result" "$scratch/findings.json" "security-reports/$scanner.json" "$scratch/raw.log"
cat "security-reports/$scanner.txt"
exit "$result"
