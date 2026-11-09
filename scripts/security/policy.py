"""Reject scanner-native bypasses; accepted findings need a reviewed policy change."""

import re
import subprocess
from pathlib import Path

NATIVE_FILES = {
    '.gitleaks.toml', '.gitleaksignore', '.trivyignore', '.trivyignore.yaml',
    '.semgrepignore', '.semgrep.yml', '.semgrep.yaml', '.bandit',
    'zizmor.yml', 'zizmor.yaml',
}
INLINE = re.compile(
    r'(?:#|//|/\*)\s*(?:nosec\b|nosemgrep\b|gitleaks:allow\b|zizmor:\s*ignore\b|trivy:ignore\b)'
)


def violations(paths: list[Path]) -> list[str]:
    errors = []
    for path in paths:
        if path.name in NATIVE_FILES:
            errors.append(f'{path}: native suppression file is prohibited')
        if path.parts[0] in {'app', 'ai_adapter', 'web', '.github'} and path.is_file():
            text = path.read_text(errors='replace')
            if INLINE.search(text):
                errors.append(f'{path}: inline scanner suppression is prohibited')
    return errors


if __name__ == '__main__':
    files = subprocess.check_output(['git', 'ls-files', '-z']).decode().split('\0')
    errors = violations([Path(name) for name in files if name])
    for error in errors:
        print(error)
    raise SystemExit(bool(errors))
