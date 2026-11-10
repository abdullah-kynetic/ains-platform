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


def test_only_trusted_main_pushes_can_publish_after_ci():
    condition = WORKFLOW["jobs"]["build"]["if"]
    assert "github.ref == 'refs/heads/main'" in condition
    assert "github.event.workflow_run.event == 'push'" in condition
    assert "github.event.workflow_run.head_repository.full_name == github.repository" in condition


def test_package_name_is_lowercase_and_image_links_to_repository():
    name = WORKFLOW["env"]["IMAGE"]
    assert name == name.lower()
    steps = WORKFLOW["jobs"]["build"]["steps"]
    build = next(step for step in steps if step.get("id") == "build")
    assert build["with"]["push"] is True
    assert (
        "org.opencontainers.image.source=https://github.com/abdullah-kynetic/ains-platform"
        in (build["with"]["labels"])
    )
    checkout = steps[0]
    assert checkout["with"]["persist-credentials"] is False


def test_digest_is_passed_as_data_to_summary():
    step = WORKFLOW["jobs"]["build"]["steps"][-1]
    assert step["env"]["IMAGE_DIGEST"] == "${{ steps.build.outputs.digest }}"
    assert "${{" not in step["run"]


def test_image_source_must_be_on_canonical_main_before_registry_login(tmp_path):
    import os
    import subprocess

    script = Path(".github/scripts/verify-image-source.sh").resolve()
    repo = tmp_path / "repo"
    repo.mkdir()

    def git(*args):
        return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()

    git("init", "-q")
    git("config", "user.name", "Synthetic test")
    git("config", "user.email", "synthetic@example.test")
    git("commit", "--allow-empty", "-qm", "trusted")
    trusted = git("rev-parse", "HEAD")
    git("update-ref", "refs/remotes/origin/main", trusted)
    git("commit", "--allow-empty", "-qm", "untrusted")
    untrusted = git("rev-parse", "HEAD")
    for sha, expected in [(untrusted, 3), ("main", 2), ("--help", 2), (trusted, 0)]:
        result = subprocess.run(
            ["bash", str(script)],
            cwd=repo,
            env={**os.environ, "BUILD_SHA": sha},
            capture_output=True,
            text=True,
        )
        assert result.returncode == expected
    assert git("rev-parse", "HEAD") == trusted
    steps = WORKFLOW["jobs"]["build"]["steps"]
    assert steps[0]["with"]["ref"] == "main"
    assert steps[0]["with"]["fetch-depth"] == 0
    assert steps[1]["run"] == "bash .github/scripts/verify-image-source.sh"
    assert any(step.get("uses", "").startswith("docker/login-action@") for step in steps[2:])


def test_runtime_base_is_digest_pinned_and_dependencies_remain_frozen():
    import re

    dockerfile = Path("Dockerfile").read_text()
    assert re.search(r"^FROM python:3\.12-alpine@sha256:[a-f0-9]{64}$", dockerfile, re.M)
    assert "uv sync --frozen --no-dev" in dockerfile
    assert "\nUSER ains\n" in dockerfile
