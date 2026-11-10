# S-11: Private configuration and public variable names

Date: 2026-11-10 (America/Los_Angeles). Source commit: this pull request head.

Database URLs and demo passwords are SecretStr values. Database/Alembic adapters unwrap them only at connection boundaries; demo seeding uses Settings. Static checks require direct application environment reads to remain in app/config.py. Browser environment names are explicitly allowlisted; git-secret scans are required in Security CI.

Proof: `tests/security/test_no_secrets_in_public_env.py`.
Command: `UV_CACHE_DIR=/tmp/kien-uv-cache uv run pytest -q tests/security`.
Result: 58 passed, one existing Starlette deprecation warning.
Full CI/Security and independent verification remain merge gates. Synthetic data only;
no live server, email, malware or real-client-data claim is made.
