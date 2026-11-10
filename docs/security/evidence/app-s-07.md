# S-07: Rate limits and lockout

Date: 2026-11-10 (America/Los_Angeles). Source commit: this pull request head.

Reuses the behavioral per-address request/concurrent-upload limits and password lockout/isolation cases. Recovery windows and PostgreSQL lockout concurrency remain covered by the existing lockout suites.

Proof: `tests/security/test_rate_limits.py`.
Command: `UV_CACHE_DIR=/tmp/kien-uv-cache uv run pytest -q tests/security`.
Result: 58 passed, one existing Starlette deprecation warning.
Full CI/Security and independent verification remain merge gates. Synthetic data only;
no live server, email, malware or real-client-data claim is made.
