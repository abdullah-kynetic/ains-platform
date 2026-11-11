# Storage, retention, export and erasure (L2-7)

Code: `app/retention.py`, `app/storage/s3.py` (`delete_receipt`), `app/config.py`
(`RECORD_RETENTION_DAYS`). No migration, no HTTP route. Synthetic data only.

## What already existed (verified by `tests/test_s3_storage.py`, `test_upload_scanning.py`)

R2/S3 upload with SHA-256, firm-scoped keys, 300 s presigned links, authorization on every
download (`app/api/downloads.py`), ClamAV scan before storage (fail closed), archive-bomb limits.
These were run against moto, not a live bucket or clamd. Live R2 and ClamAV evidence belongs to
Lane C.

## What this piece adds

- **Fix:** an R2 upload no longer fails. R2 has no versioning and returns no `VersionId`;
  ingestion crashed with `KeyError`. It now stores version `1`.
- **Operator commands** (run by Abdullah or Lane C with the real database and bucket settings):
  - `uv run python -m app.retention export --firm-id ID [--out FILE]`
  - `uv run python -m app.retention plan --firm-id ID`
  - `uv run python -m app.retention erase --firm-id ID --confirm` (without `--confirm` it only plans)
- **Export** contains only what the client may already see: their users' names and emails,
  engagements, checklist titles and states, upload metadata with SHA-256, released response
  requests and replies, sent and paid invoices, and the signed report without findings. No
  findings, workpapers, password data or other firms.
- **Erase** deletes the stored bytes of eligible uploads (every object version), then replaces
  the receipt with `erased:<id>`. Rows, hashes and the audit chain stay, so each file's existence
  and fingerprint remain provable. A failed delete is counted and never recorded as erased. One
  `firm_data.erased` entry (counts only) is written to the firm's audit chain.
- By inspection of `downloads.py`, an erased document's download now answers 404 (the receipt no
  longer matches the bucket prefix). Not covered by an automated test here.

## Rule implemented

Evidence of a **completed** engagement (partner signature, completion or final report) is kept
for `RECORD_RETENTION_DAYS` after completion. Evidence of an engagement that was never signed, or
whose window has passed, is erasable on request. Objects under an S3 Object Lock refuse deletion
and are reported as failed.

## Decisions for Abdullah and the attorney

- **The 2190 days (six years) default is a placeholder, not legal advice.** The attorney should
  set the real period; it is one environment variable.
- Whether a client can force early erasure of a completed engagement's evidence: this build says no.
- The export covers client-visible data only; a regulator-grade export of the whole audit file
  is not built.
- Erasure removes files but leaves names and numbers of documents in the database and audit chain.
  Removing those too needs a policy decision.
- Not done: automatic expiry, an HTTP route for firms to request export or erasure, erasure of
  Egnyte-stored files (skipped and listed), and the live R2 Object Lock rule on the
  final-report prefix (Lane C).
