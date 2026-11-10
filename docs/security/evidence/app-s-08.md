# S-08: Registered cross-tenant denial coverage

Date: 2026-11-10 (America/Los_Angeles). Source commit: this pull request head.

A new protected route fails until it has an explicit scope-policy case. Every route requires the central identity dependency. Foreign clients and revoked auditor assignments are checked against real resource IDs; collections must omit foreign records. Session-only scope is also proved by S-06.

Proof: `tests/security/test_tenant_isolation.py`.
Command: `UV_CACHE_DIR=/tmp/kien-uv-cache uv run pytest -q tests/security`.
Result: 58 passed, one existing Starlette deprecation warning.
Full CI/Security and independent verification remain merge gates. Synthetic data only;
no live server, email, malware or real-client-data claim is made.
