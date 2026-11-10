# S-14: Server-side role authorization

Date: 2026-11-10 (America/Los_Angeles). Source commit: this pull request head.

Every nonpublic route refuses a missing session; every auditor route refuses the client role using a valid request shape. S-08 additionally verifies identity dependencies and real cross-tenant resources; UI gates are not used as authorization.

Proof: `tests/security/test_authorization.py`.
Command: `UV_CACHE_DIR=/tmp/kien-uv-cache uv run pytest -q tests/security`.
Result: 58 passed, one existing Starlette deprecation warning.
Full CI/Security and independent verification remain merge gates. Synthetic data only;
no live server, email, malware or real-client-data claim is made.
