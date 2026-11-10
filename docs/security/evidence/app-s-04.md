# S-04: Auditor MFA and recovery codes

Date: 2026-11-09 (America/Los_Angeles). Source commit: `3da653e6ecfc5accb78b8293daebdff9be64a708`.

After MFA is disabled, an already-issued auditor session cannot reach any inventoried auditor route. Authenticated sign-out remains possible. Recovery codes are hashed and single-use.

Proof: `tests/security/test_auditor_mfa.py`.
Command executed: `UV_CACHE_DIR=/tmp/kien-uv-cache uv run pytest -q tests/security`.
Result: 15 passed, one existing Starlette dependency deprecation warning.
The broader auth/reset/API focused run passed 70 tests. Full CI, Security and
independent verification remain required before merge. Synthetic data only;
no email delivery, live-host or operational-security claim is made.
