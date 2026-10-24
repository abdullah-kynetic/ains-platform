# Backup restore drill

Production writes a daily custom-format `pg_dump` to the ops bucket. This
runbook restores that archive into a separate Postgres database and checks
that every public base table has a row count. The automated drill in this
repository uses synthetic rows only. A downloaded production dump holds real
client records: keep it on the operator workstation, record counts only, and
delete the local copy when the drill is finished.

Leave the Terraform configuration, remote state, IAM policies, bucket
lifecycle rules, and existing S3 backup objects unchanged.

## Scheduled backup

Host bootstrap installs `/etc/ains/backup.sh` and `ains-backup.timer`
(`infra/aws/user-data.sh.tftpl`). The timer fires daily at 09:30 UTC and runs:

```sh
sudo -u postgres pg_dump -Fc ains \
  | aws s3 cp - "s3://${OPS_BUCKET}/backups/ains-${STAMP}.dump" \
      --sse AES256 --region "${REGION}"
```

`STAMP` is UTC `YYYYMMDDTHHMMSSZ`. `OPS_BUCKET` is the Terraform output
`ops_bucket`. `REGION` is the deployment region (`us-east-2` on the lean
profile). Objects under `backups/` expire after `backup_retention_days`
(14 by default). There is no point-in-time recovery; the newest object is
the recovery point, and a host loss can drop up to one day of writes.

The application instance role may `s3:PutObject` to `backups/*`. It cannot
list or download those objects. Download with an operator identity that
already has read access to the ops bucket.

## Synthetic drill

This path does not contact AWS and does not read a production database. It
needs `initdb`, `pg_ctl`, `pg_dump`, and `pg_restore` from the same PostgreSQL
major version (16 in production). On Debian and Ubuntu those programs live in
`/usr/lib/postgresql/16/bin` even when `initdb` is absent from `PATH`. The
script searches that directory.

```sh
uv run python scripts/backup_restore.py
uv run pytest tests/test_backup_restore.py -q
```

The script starts Postgres on a private Unix socket with TCP listening
disabled, creates database `ains_source`, loads one mock firm
(`synthetic-restore-drill`, `example.com` users, a `synthetic://` document
path, and no document body), writes `pg_dump -Fc`, restores into
`ains_restore`, and prints a count for every public base table. Exit 0 means
the counts match the seeded mock population. Exit 1 means a count differed.
Exit 2 means the Postgres tools are missing, or an argument was passed.

`tests/test_backup_restore.py` runs the same dump, restore, and comparison.
It skips when the four binaries are not installed. Backend CI installs
PostgreSQL 16 before pytest so the drill runs on pull requests. The script
accepts no dump path, database URL, or S3 URI.

Seeded mock counts:

| Table | Rows |
| --- | ---: |
| `firms` | 1 |
| `users` | 2 |
| `engagements` | 1 |
| `checklist_item_instances` | 2 |
| `documents` | 1 |
| `audit_logs` | 1 |

Every other application table is present and empty, and those zeros are
compared too.

## Fetch a dump from S3

Run this on an operator workstation with existing AWS CLI credentials. Use
the ops bucket name already recorded from `terraform output ops_bucket`
during provision.

```sh
export AWS_REGION=us-east-2
export OPS_BUCKET="<ops_bucket output>"
aws s3 ls "s3://${OPS_BUCKET}/backups/" --region "$AWS_REGION"
aws s3 cp "s3://${OPS_BUCKET}/backups/ains-YYYYMMDDTHHMMSSZ.dump" \
  ./ains-restore-drill.dump --region "$AWS_REGION"
```

Confirm the object is a custom-format archive before restoring it:

```sh
pg_restore -l ./ains-restore-drill.dump | head
```

The file begins with the bytes `PGDMP`. `*.dump` is gitignored. Restore with
PostgreSQL 16 client tools so the client major version matches the server
that created the archive.

## Restore into local Postgres

Restore into a new empty database named `ains_restore_drill`. Keep the live
production database `ains` on the EC2 host unchanged. Run `pg_restore` here,
on the workstation.

### Docker Compose Postgres 16

Use the local development database from `docker compose`. Start it only when
that volume holds no client records.

```sh
docker compose up -d --wait
docker compose exec -T postgres psql -U ains -d postgres -v ON_ERROR_STOP=1 \
  -c "CREATE DATABASE ains_restore_drill"
docker compose cp ./ains-restore-drill.dump postgres:/tmp/ains-restore-drill.dump
docker compose exec -T postgres pg_restore \
  --exit-on-error --single-transaction --no-owner --no-acl \
  -U ains -d ains_restore_drill /tmp/ains-restore-drill.dump
```

`--no-owner` and `--no-acl` apply objects as the local `ains` role. The
archive remembers the production owner, and that role does not exist in the
local cluster.

### Workstation cluster

```sh
createdb ains_restore_drill
pg_restore --exit-on-error --single-transaction --no-owner --no-acl \
  -d ains_restore_drill ./ains-restore-drill.dump
```

## Compare row counts

The archive is a point-in-time copy. Writes after 09:30 UTC show up on the
live server and are absent from that object. For a strict reading, compare
the restored database with counts taken from production at the dump
timestamp, and treat later inserts as drift. The synthetic script is the
strict automated match: it dumps and restores one mock database in a single
run.

Run this read-only query on the restored database. It counts every ordinary
table in `public` (the same set the synthetic script counts):

```sh
docker compose exec -T postgres psql -U ains -d ains_restore_drill -v ON_ERROR_STOP=1 -c "
SELECT n.nspname AS schema_name,
       c.relname AS table_name,
       (xpath('/row/c/text()', query_to_xml(
          format('select count(*) as c from %I.%I', n.nspname, c.relname),
          false, true, '')))[1]::text::bigint AS row_count
FROM pg_catalog.pg_class AS c
JOIN pg_catalog.pg_namespace AS n ON n.oid = c.relnamespace
WHERE n.nspname = 'public' AND c.relkind = 'r'
ORDER BY table_name;
"
```

To read the live source, open SSM with the existing instance id (Terraform
output `instance_id`) and run that same `SELECT` only:

```sh
aws ssm start-session --target INSTANCE_ID --region us-east-2
sudo -u postgres psql -d ains -v ON_ERROR_STOP=1 -c "<SELECT above>"
```

Compare the two result sets by `table_name`. A successful restore has every
public base table from the archive, with the same count as the source
snapshot for that object. A restored zero on a table that had rows at dump
time means the archive or the restore is incomplete.

Record the object key, the restore target (`ains_restore_drill` on the
workstation), the count table, and pass or fail. Omit row contents, document
names, and connection strings from the evidence note.

## Cleanup

```sh
docker compose exec -T postgres psql -U ains -d postgres -v ON_ERROR_STOP=1 \
  -c "DROP DATABASE IF EXISTS ains_restore_drill"
docker compose exec -T postgres rm -f /tmp/ains-restore-drill.dump
rm -f ./ains-restore-drill.dump
```

Leave the S3 object in place. Lifecycle expiration removes it when
`backup_retention_days` elapses. Dropping `ains_restore_drill` removes only
the scratch database created above.

## When to run

Run `scripts/backup_restore.py` when backup or schema code changes. Run the
manual S3 restore before treating backups as recovery evidence, and again
after a Postgres major upgrade or a change to the dump format. A failed
`ains-backup.service` needs a fresh successful upload while the previous
object is still inside the retention window.
