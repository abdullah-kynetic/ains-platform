# S-02: Production cookie flags

Date: 2026-11-09 (America/Los_Angeles). Source commit: `3da653e6ecfc5accb78b8293daebdff9be64a708`.

Login and deletion cookies are HttpOnly, Secure with production settings, SameSite=Lax, Path=/ and host-only (no Domain). Login max-age is 12 hours; deletion max-age is zero.

Proof: `tests/security/test_cookies.py`.
Command executed: `UV_CACHE_DIR=/tmp/kien-uv-cache uv run pytest -q tests/security`.
Result: 15 passed, one existing Starlette dependency deprecation warning.
The broader auth/reset/API focused run passed 70 tests. Full CI, Security and
independent verification remain required before merge. Synthetic data only;
no email delivery, live-host or operational-security claim is made.
