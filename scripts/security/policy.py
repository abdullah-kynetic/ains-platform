"""Reject scanner-native bypasses; accepted findings need a reviewed policy change."""

import argparse
import json
import re
import subprocess
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

NATIVE_FILES = {
    ".gitleaks.toml",
    ".gitleaksignore",
    ".trivyignore",
    ".trivyignore.yaml",
    ".semgrepignore",
    ".semgrep.yml",
    ".semgrep.yaml",
    ".bandit",
    "zizmor.yml",
    "zizmor.yaml",
}
INLINE = re.compile(
    r"(?:#|//|/\*)\s*(?:nosec\b|nosemgrep\b|gitleaks:allow\b|zizmor:\s*ignore\b|trivy:ignore\b)"
)


def violations(paths: list[Path]) -> list[str]:
    errors = []
    for path in paths:
        if path.name in NATIVE_FILES:
            errors.append(f"{path}: native suppression file is prohibited")
        if path.parts[0] in {"app", "ai_adapter", "web", ".github"} and path.is_file():
            text = path.read_text(errors="replace")
            if INLINE.search(text):
                errors.append(f"{path}: inline scanner suppression is prohibited")
    return errors


def accepted_risks(path: Path, today: date | None = None) -> list[dict]:
    today = today or datetime.now(UTC).date()
    blocks = re.findall(r"```json\n(.*?)\n```", path.read_text(), re.S)
    if len(blocks) != 1:
        raise ValueError("Exactly one accepted-risk JSON block is required")
    entries = json.loads(blocks[0])
    if not isinstance(entries, list):
        raise ValueError("Accepted risks must be a list")
    seen = set()
    for entry in entries:
        required = {"scanner", "finding", "scope", "reason", "owner", "approved", "expires"}
        if not isinstance(entry, dict) or not required <= entry.keys():
            raise ValueError("Incomplete accepted risk")
        if any(not isinstance(value, str) or not value.strip() for value in entry.values()):
            raise ValueError("Empty or invalid accepted risk field")
        approved = date.fromisoformat(entry["approved"])
        expires = date.fromisoformat(entry["expires"])
        if (
            approved > today
            or expires <= today
            or not approved < expires <= approved + timedelta(days=90)
        ):
            raise ValueError("Expired or invalid accepted risk lifetime")
        scanner, finding, scope = (entry[key] for key in ["scanner", "finding", "scope"])
        if scanner == "gitleaks":
            fingerprint = entry.get("fingerprint", "")
            pattern = (
                r"[0-9a-f]{40}:" + re.escape(scope) + ":" + re.escape(finding) + r":[1-9][0-9]*"
            )
            if not re.fullmatch(pattern, fingerprint):
                raise ValueError("Gitleaks exceptions require exact historical fingerprints")
            key = (scanner, fingerprint)
        elif (
            scanner == "zizmor"
            and finding == "dangerous-triggers"
            and scope == ".github/workflows/image.yml"
        ):
            key = (scanner, finding, scope)
        elif scanner in {"semgrep", "trivy-fs"}:
            if entry.get("review") != "Stage 2 security audit":
                raise ValueError("Scoped exceptions require Stage 2 review")
            if Path(scope).is_absolute() or ".." in Path(scope).parts or "*" in scope:
                raise ValueError("Exceptions require an exact relative file")
            pattern = r"AWS-[0-9]{4}" if scanner == "trivy-fs" else r"[a-zA-Z0-9_.-]+"
            if not re.fullmatch(pattern, finding):
                raise ValueError("Invalid scoped finding ID")
            key = (scanner, finding, scope)
        else:
            raise ValueError("Unsupported accepted risk")
        if key in seen:
            raise ValueError("Duplicate accepted risk")
        seen.add(key)
    return entries


def generate(directory: Path, entries: list[dict]) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    fingerprints = [e["fingerprint"] for e in entries if e["scanner"] == "gitleaks"]
    (directory / "gitleaksignore").write_text("\n".join(fingerprints) + "\n")
    rules = {}
    for entry in entries:
        if entry["scanner"] != "zizmor":
            continue
        # Bind the exception to the reviewed trigger line, never the entire file.
        lines = Path(entry["scope"]).read_text().splitlines()
        line = next(i for i, text in enumerate(lines, 1) if text == "  workflow_run:")
        rules[entry["finding"]] = {"ignore": [f"image.yml:{line}"]}
    # JSON is valid YAML and avoids adding dependencies to this policy runner.
    (directory / "zizmor.yml").write_text(json.dumps({"rules": rules}))


def apply_filter(scanner: str, status: int, path: Path, entries: list[dict]) -> int:
    # Only documented finding exit code 1 can be cleared; runtime errors stay red.
    if status != 1 or scanner not in {"semgrep", "trivy-fs"}:
        return status
    data = json.loads(path.read_text())
    if not isinstance(data, dict):
        raise ValueError("Invalid scanner report")
    approved = {(e["finding"], e["scope"]): e for e in entries if e["scanner"] == scanner}
    accepted, total, remaining = [], 0, 0

    def keep(finding, scope):
        nonlocal total, remaining
        total += 1
        risk = approved.get((finding, scope))
        if risk:
            accepted.append(
                {
                    "id": finding,
                    "location": scope,
                    "expires": risk["expires"],
                    "review": risk["review"],
                }
            )
            return False
        remaining += 1
        return True

    if scanner == "semgrep":
        results = data["results"]
        if not isinstance(results, list):
            raise ValueError("Invalid Semgrep findings")
        data["results"] = [r for r in results if keep(r["check_id"], r["path"])]
    else:
        results = data["Results"]
        if not isinstance(results, list):
            raise ValueError("Invalid Trivy findings")
        for result in results:
            # Only misconfigurations can match approved AWS rules. Never secrets/vulns.
            remaining += len(result.get("Secrets") or []) + len(result.get("Vulnerabilities") or [])
            result["Misconfigurations"] = [
                r
                for r in (result.get("Misconfigurations") or [])
                if keep(r["ID"], result["Target"])
            ]
    data["KienAcceptedFindings"] = accepted
    path.write_text(json.dumps(data))
    return 0 if total > 0 and remaining == 0 and not data.get("errors") else status


def filter_report(scanner: str, status: int, path: Path, entries: list[dict]) -> int:
    try:
        return apply_filter(scanner, status, path, entries)
    except (ValueError, OSError, KeyError, TypeError):
        # Missing/malformed scanner JSON can never clear a failing scanner.
        return status


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--filter-report", choices=["semgrep", "trivy-fs"])
    parser.add_argument("--report", type=Path)
    parser.add_argument("--status", type=int)
    args = parser.parse_args()
    try:
        entries = accepted_risks(Path("docs/security/accepted-risks.md"))
        if args.filter_report:
            if args.report is None or args.status is None:
                raise ValueError("Missing scanner report arguments")
            print(filter_report(args.filter_report, args.status, args.report, entries))
        elif args.output_dir:
            generate(args.output_dir, entries)
        else:
            files = subprocess.check_output(["git", "ls-files", "-z"]).decode().split("\0")
            errors = violations([Path(name) for name in files if name])
            for error in errors:
                print(error)
            raise SystemExit(bool(errors))
    except (ValueError, OSError, StopIteration, KeyError, TypeError):
        raise SystemExit("Invalid accepted-risk policy; no suppression applied") from None
