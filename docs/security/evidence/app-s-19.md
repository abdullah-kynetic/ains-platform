# S-19: Authorized downloads and short-lived links

Date: 2026-11-10. Source commit: this pull request head.

Downloads are served only by `GET /engagements/{id}/documents/{doc}/download` (client) and
`GET /auditor/engagements/{id}/documents/{doc}/download` (auditor). Each request needs a session,
the engagement scope (auditor assigned, or client of the same firm), a document of that
engagement and firm, a storage receipt under that firm's prefix, and an unrestricted item. The
reply is a presigned link valid for 60 seconds. The audit chain records who asked, never the URL.

Proof: `tests/security/test_downloads.py` (moto S3, synthetic data). Cross-tenant, unassigned,
wrong-role, anonymous, foreign-receipt and restricted-item cases are denied.
Command: `uv run pytest -q tests/security`.
Not claimed: the live anonymous GET returning 403 and the bucket's public-access block are Lane C
checks on the real bucket.
