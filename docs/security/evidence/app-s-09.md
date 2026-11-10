# S-09: Client field isolation

Date: 2026-11-09 (America/Los_Angeles). Source commit: `cff0fab`.

All client read/mutation contracts must be registered. Released request text is allowed; recursive finding-field checks and seeded private markers prevent internal findings, notes, tasks and draft reports from being serialized.

Proof: `tests/security/test_client_fields.py`.
Command: `UV_CACHE_DIR=/tmp/kien-uv-cache uv run pytest -q tests/security`.
Result: 53 passed, one existing Starlette deprecation warning.
Full CI/Security and independent verification remain merge gates. Synthetic data only;
no live server, email, malware or real-client-data claim is made.
