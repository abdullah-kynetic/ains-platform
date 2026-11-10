"""Export allowlisted finding metadata; never export source snippets or secret values."""

import json
import sys
from pathlib import Path


def findings(scanner: str, raw: str) -> list[dict]:
    try:
        data = json.loads(raw)
    except ValueError:
        try:
            data = [json.loads(line) for line in raw.splitlines() if line.strip()]
        except ValueError:
            return []
    rows = []

    def add(rule, location, severity="unknown", **metadata):
        rows.append({"id": str(rule), "location": str(location), "severity": str(severity),
                     **{key: str(value) for key, value in metadata.items() if value}})

    if scanner == "pip-audit":
        for dep in data.get("dependencies", []):
            for vuln in dep.get("vulns", []):
                add(vuln.get("id"), dep.get("name"))
    elif scanner == "npm":
        for name, vuln in data.get("vulnerabilities", {}).items():
            add(name, name, vuln.get("severity"))
    elif scanner == "gitleaks":
        for entry in data:
            add(entry.get("RuleID"), entry.get("File"), "secret")
    elif scanner == "trufflehog":
        entries = data if isinstance(data, list) else [data]
        for entry in entries:
            if entry.get("Verified"):
                source = entry.get("SourceMetadata", {}).get("Data", {}).get("Git", {})
                add(entry.get("DetectorName"), source.get("file"), "verified secret")
    elif scanner.startswith("trivy-"):
        for result in data.get("Results", []):
            for category, key in [("Vulnerabilities", "VulnerabilityID"),
                                  ("Misconfigurations", "ID"), ("Secrets", "RuleID")]:
                for entry in result.get(category, []):
                    metadata = {}
                    if category == "Vulnerabilities":
                        metadata = {"package": entry.get("PkgName"),
                                    "installed": entry.get("InstalledVersion"),
                                    "fixed": entry.get("FixedVersion")}
                    add(entry.get(key), result.get("Target"), entry.get("Severity"), **metadata)
    elif scanner == "semgrep":
        for entry in data.get("results", []):
            add(entry.get("check_id"), entry.get("path"), entry.get("extra", {}).get("severity"))
    elif scanner == "bandit":
        for entry in data.get("results", []):
            add(entry.get("test_id"), entry.get("filename"), entry.get("issue_severity"))
    elif scanner == "zizmor":
        for entry in data:
            add(
                entry.get("ident"), ".github/workflows",
                entry.get("determinations", {}).get("severity"),
            )
    return rows


if __name__ == "__main__":
    scanner, status, source, target, *logs = sys.argv[1:]
    try:
        rows = findings(scanner, Path(source).read_text())
    except (OSError, AttributeError, TypeError):
        rows = []
    diagnostics = []
    if logs:
        try:
            log = Path(logs[0]).read_text(errors="replace").lower()
        except OSError:
            log = ""
        for label, needles in {
            "certificate-verification": ["certificate verify failed", "unknown authority"],
            "network-denied": ["domain forbidden", "403 forbidden"],
            "network-unavailable": ["connection refused", "connection timed out"],
            "read-only-filesystem": ["read-only file system"],
        }.items():
            if any(needle in log for needle in needles):
                diagnostics.append(label)
    Path(target).write_text(json.dumps({
        "scanner": scanner, "exit_status": int(status), "findings": rows,
        "diagnostics": diagnostics,
        "note": "Only finding IDs, locations and severities are exported. "
                "Nonzero status without findings can indicate a tool or network error.",
    }, indent=2) + "\n")

    if int(status):
        def escape(value):
            return str(value).replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")

        summary = f"{scanner}: exit {status}; findings={len(rows)}; diagnostics={diagnostics}"
        print("::error title=Security scan failed::" + escape(summary))
        metadata = [" | ".join(str(value) for value in row.values()) for row in rows]
        if metadata:
            # GitHub retains only a limited number of error annotations per step.
            # Aggregate safe metadata so later package findings remain retrievable.
            print("::error title=Security finding metadata::" + escape("\n".join(metadata)))
