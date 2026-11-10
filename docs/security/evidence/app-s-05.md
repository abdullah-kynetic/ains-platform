# S-05: Invite-only client access

Date: 2026-11-09 (America/Los_Angeles). Source commit: `3da653e6ecfc5accb78b8293daebdff9be64a708`.

No signup/registration path exists. Unknown-user password login creates no account. Expired and replayed invitation tokens return 410 and no cookie; a valid invitation creates exactly one client.

Proof: `tests/security/test_invite_only.py`.
Command executed: `UV_CACHE_DIR=/tmp/kien-uv-cache uv run pytest -q tests/security`.
Result: 15 passed, one existing Starlette dependency deprecation warning.
The broader auth/reset/API focused run passed 70 tests. Full CI, Security and
independent verification remain required before merge. Synthetic data only;
no email delivery, live-host or operational-security claim is made.
