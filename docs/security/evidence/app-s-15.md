# S-15: Report HTML sanitizer

Date: 2026-11-10 (America/Los_Angeles). Source commit: this pull request head.

Only approved formatting tags survive. Attributes, executable elements, embedded resources and active URL attributes are removed; sanitized content is idempotent. Synthetic script/frame markers cannot survive.

Proof: `tests/security/test_report_sanitizer.py`.
Command: `UV_CACHE_DIR=/tmp/kien-uv-cache uv run pytest -q tests/security`.
Result: 58 passed, one existing Starlette deprecation warning.
Full CI/Security and independent verification remain merge gates. Synthetic data only;
no live server, email, malware or real-client-data claim is made.
