# Backups

- `backup.sh` (nightly): dumps Postgres to a work file, validates it (`pg_restore --list`, non-empty,
  has table data) and only then writes a restic snapshot tagged `db` and `validated`, together with
  row counts taken before and after the dump. A failed or truncated dump never becomes a snapshot.
  Config snapshots (`config` tag) are thinned: 7 daily, 4 weekly, 3 monthly (override with
  `KEEP_CONFIG_*`). Database retention is 14 daily, 8 weekly, 6 monthly (`KEEP_*`).
- `restore-drill.sh` restores the latest validated snapshot into a scratch container and compares
  row counts with the counts recorded at backup time (never the live database).
- `lock-drill.sh` checks restic and `rclone --immutable --checksum` against the bucket lock rules.

## Keys must live off the server

The restic password (`RESTIC_PASSWORD_FILE`, normally `/etc/kien/restic.pass`), the read-only restore
token and the passphrase for the secrets bundle are stored in the owner's password manager and a
printed offline copy. The server copy is only a convenience: if the server is lost, the
`/etc/kien` directory is lost with it, so without an off-server copy the encrypted backups cannot be
read. Only variable names appear in this repository (see `restic.env.example`).
