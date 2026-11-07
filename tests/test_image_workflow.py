from pathlib import Path

import yaml

WORKFLOW = yaml.safe_load(Path(".github/workflows/image.yml").read_text())
# PyYAML parses the bare key "on" as boolean True.
TRIGGERS = WORKFLOW.get("on") or WORKFLOW[True]


def test_image_builds_only_after_ci_succeeds_on_main():
    assert TRIGGERS["workflow_run"]["workflows"] == ["CI"]
    assert TRIGGERS["workflow_run"]["branches"] == ["main"]
    assert "conclusion == 'success'" in WORKFLOW["jobs"]["build"]["if"]
    assert "pull_request" not in TRIGGERS


def test_permissions_are_minimal_and_no_extra_secrets_used():
    assert WORKFLOW["permissions"] == {"contents": "read"}
    assert WORKFLOW["jobs"]["build"]["permissions"] == {"contents": "read", "packages": "write"}
    text = Path(".github/workflows/image.yml").read_text()
    assert text.count("secrets.") == 1 and "secrets.GITHUB_TOKEN" in text


def test_image_is_tagged_by_sha_and_published_to_ghcr():
    text = Path(".github/workflows/image.yml").read_text()
    assert "ghcr.io/abdullah-kynetic/ains-platform" in text
    assert ":sha-" in text and "steps.build.outputs.digest" in text
