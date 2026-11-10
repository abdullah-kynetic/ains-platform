# S-13: Append-only audit chain

Date: 2026-11-10 (America/Los_Angeles). Source commit: this pull request head.

Existing behavioral tests verify linked hashes, privileged tamper detection, and ORM/bulk mutation rejection. PostgreSQL UPDATE/DELETE/TRUNCATE protection is covered by tests/test_audit_postgres.py; local binaries are unavailable, so its strict CI service job is required.

Proof: `tests/security/test_audit_chain.py`.
Command: `UV_CACHE_DIR=/tmp/kien-uv-cache uv run pytest -q tests/security`.
Result: 58 passed, one existing Starlette deprecation warning.
Full CI/Security and independent verification remain merge gates. Synthetic data only;
no live server, email, malware or real-client-data claim is made.
