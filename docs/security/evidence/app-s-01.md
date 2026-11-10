# S-01: Argon2id and password upgrades

Date: 2026-11-09 (America/Los_Angeles). Source commit: `3da653e6ecfc5accb78b8293daebdff9be64a708`.

Salted stored hashes start with `$argon2id$`, reject incorrect passwords, and never contain the synthetic plaintext. Successful login upgrades older Argon2 parameters and persists the upgraded hash.

Proof: `tests/security/test_password_hashing.py`.
Command executed: `UV_CACHE_DIR=/tmp/kien-uv-cache uv run pytest -q tests/security`.
Result: 15 passed, one existing Starlette dependency deprecation warning.
The broader auth/reset/API focused run passed 70 tests. Full CI, Security and
independent verification remain required before merge. Synthetic data only;
no email delivery, live-host or operational-security claim is made.
