# S-12: Private application logs and telemetry

Date: 2026-11-10 (America/Los_Angeles). Source commit: this pull request head.

Uvicorn access logs retain method, HTTP version and status while withholding client addresses,
paths and query strings. Uvicorn error tracebacks are replaced with a fixed message. Sentry events
are rebuilt from safe numeric frame metadata. Upload audit records retain content and signature
hashes without filenames or raw scanner text. Provider-delivery failures retain only exception type.

Proof: `tests/security/test_log_scrubbing.py`, `tests/test_upload_scanning.py`,
`tests/test_monitoring.py`, and `tests/test_report_ready_email.py`.
Command: `UV_CACHE_DIR=/tmp/kien-uv-cache uv run pytest -q tests/security/test_log_scrubbing.py tests/test_upload_scanning.py tests/test_monitoring.py tests/test_report_ready_email.py`.
Result: 32 passed, one existing Starlette deprecation warning.
Full CI/Security and independent verification remain merge gates. Synthetic data only;
no live server, provider delivery, malware or real-client-data claim is made.
