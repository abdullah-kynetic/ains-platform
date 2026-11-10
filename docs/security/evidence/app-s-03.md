# S-03: CSRF coverage for every unsafe route

Date: 2026-11-09 (America/Los_Angeles). Source commit: `3da653e6ecfc5accb78b8293daebdff9be64a708`.

Every POST, PUT, PATCH and DELETE in route_inventory.txt rejects a foreign Origin before authorization/body validation. No cookie, upload or audit mutation is produced. The test automatically includes newly inventoried routes.

Proof: `tests/security/test_csrf.py`.
Command executed: `UV_CACHE_DIR=/tmp/kien-uv-cache uv run pytest -q tests/security`.
Result: 15 passed, one existing Starlette dependency deprecation warning.
The broader auth/reset/API focused run passed 70 tests. Full CI, Security and
independent verification remain required before merge. Synthetic data only;
no email delivery, live-host or operational-security claim is made.
