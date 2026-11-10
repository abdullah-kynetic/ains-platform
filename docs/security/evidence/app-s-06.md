# S-06: Session expiry, revocation and identity binding

Date: 2026-11-09 (America/Los_Angeles). Source commit: `3da653e6ecfc5accb78b8293daebdff9be64a708`.

JWT expiry and database session expiry independently return 401. Revoked sid and signed-out tokens return 401. Reset revokes all own sessions while preserving another user. ORM role/firm changes atomically revoke sessions and append a hash-chained system event; rollback preserves the old session. JWT role/firm claims also reject stale identities. Legacy tokens without identity claims require fresh sign-in after deployment.

Proof: `tests/security/test_sessions.py`.
Command executed: `UV_CACHE_DIR=/tmp/kien-uv-cache uv run pytest -q tests/security`.
Result: 15 passed, one existing Starlette dependency deprecation warning.
The broader auth/reset/API focused run passed 70 tests. Full CI, Security and
independent verification remain required before merge. Synthetic data only;
no email delivery, live-host or operational-security claim is made.
