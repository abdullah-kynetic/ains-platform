# L1-1 image publication verification

2026-11-09; base main: `49ee4b8` (PR #91).

- Historical run 42711094683 failed while pushing `:main`: GHCR blob HEAD returned
  HTTP 403. Confirmed through the build job's check-run annotation (129480509152).
- `gh workflow run image.yml --ref main` started run
  [42721702820](https://github.com/abdullah-kynetic/ains-platform/actions/runs/42721702820).
  It completed successfully on unchanged main, including login, push and digest summary.
  The historical error no longer reproduces. No credentials or package settings changed.
- The existing job already grants `contents: read`, `packages: write`; the image
  name is already lowercase. Retained these minimum permissions.
- Added a source-repository OCI label, disabled persisted checkout credentials,
  limited privileged workflow-run publication to same-repository main pushes, and
  passed the digest through an environment variable when rendering the summary.
- `UV_CACHE_DIR=/tmp/kien-uv-cache uv run pytest -q tests/test_image_workflow.py`:
  6 passed. Independent verifier reran the same command: 6 passed; code review PASS.

BLOCKED(owner): Copy the verified digest from the successful run's summary into
`deploy/RELEASES.md`, with Deployed to: none. The environment blocks the
results-receiver.actions.githubusercontent.com log download; package read access
is unavailable (403 from GitHub Packages API; anonymous GHCR manifest read 401).
No digest has been guessed and no deployment was attempted.
