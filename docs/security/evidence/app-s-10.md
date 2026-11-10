# S-10: Upload boundaries and fail-closed scanning

Date: 2026-11-10 (America/Los_Angeles). Source commit: this pull request head.

Reuses invalid-type/zero-byte/size/restricted-item and fake-clamd failure/quarantine cases. Rejected files never reach storage. Quarantine here means rejection with metadata; real ClamAV operation is a Lane C check. Additional audit-text privacy hardening is tracked under S-12.

Proof: `tests/security/test_upload_controls.py`.
Command: `UV_CACHE_DIR=/tmp/kien-uv-cache uv run pytest -q tests/security`.
Result: 58 passed, one existing Starlette deprecation warning.
Full CI/Security and independent verification remain merge gates. Synthetic data only;
no live server, email, malware or real-client-data claim is made.
