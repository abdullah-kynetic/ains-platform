#!/usr/bin/env bash
# Restore drill (plan section 6.5). Restores the latest dump into a SCRATCH Postgres container using
# only the read-only restore token, compares row counts with the source, and checks one document.
# A backup does not count until this passes. Prints timings. Prints no secrets or row contents.
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
. "$HERE/../lib.sh"
set -a
. "${RESTORE_ENV_FILE:-/etc/kien/restore.env}" # read-only token + RESTIC_* + RCLONE remote names
set +a
export RCLONE_CONFIG=${RCLONE_CONFIG:-/etc/kien/rclone.conf}

SCRATCH=kien-restore-drill
DB_USER=drill DB_NAME=drill
START=$(date +%s)
cleanup() { docker rm -f "$SCRATCH" >/dev/null 2>&1 || true; rm -rf "${SCRATCH_TMP:-}"; }
trap cleanup EXIT
cleanup
SCRATCH_TMP=$(mktemp -d)
docker run -d --name "$SCRATCH" -e POSTGRES_USER=$DB_USER -e POSTGRES_PASSWORD="$(head -c 24 /dev/urandom | base64)" \
  -e POSTGRES_DB=$DB_NAME --network none postgres:16 >/dev/null
for _ in $(seq 1 30); do docker exec "$SCRATCH" pg_isready -U $DB_USER -d $DB_NAME >/dev/null 2>&1 && break; sleep 1; done

"$HERE/restore.sh" latest "$SCRATCH" $DB_USER $DB_NAME
RESTORED=$(date +%s)

COUNT_SQL="select table_name||'='||(xpath('/row/c/text()', query_to_xml('select count(*) c from public.'||quote_ident(table_name), false, true, '')))[1]::text from information_schema.tables where table_schema='public' and table_type='BASE TABLE' order by 1"
WORK=${KIEN_BACKUP_WORK:-/var/backups/kien-work}
# Compare with the counts recorded around the dump at backup time (never the live database):
# each restored table must hold between the "before" and "after" row counts.
restic dump latest "$WORK/kien-db.counts.before" --tag db,validated > "$SCRATCH_TMP/before"
restic dump latest "$WORK/kien-db.counts.after" --tag db,validated > "$SCRATCH_TMP/after"
docker exec "$SCRATCH" psql -U $DB_USER -d $DB_NAME -Atc "$COUNT_SQL" > "$SCRATCH_TMP/restored"
if ! awk -F= 'FNR==NR && FILENAME==ARGV[1] {lo[$1]=$2; next} FILENAME==ARGV[2] {hi[$1]=$2; next}
  {seen[$1]=1; if ($2+0 < lo[$1]+0 || $2+0 > hi[$1]+0) {print "count outside backup window: " $1 " restored=" $2 " window=" lo[$1] ".." hi[$1]; bad=1}}
  END {for (t in lo) if (!(t in seen)) {print "missing table: " t; bad=1} exit bad}' \
  "$SCRATCH_TMP/before" "$SCRATCH_TMP/after" "$SCRATCH_TMP/restored"; then
  echo "DRILL FAIL: restored row counts do not match the counts recorded at backup time" >&2
  exit 1
fi
echo "row counts match the backup-time record for $(wc -l < "$SCRATCH_TMP/restored") tables"

# One document: SHA-256 of the backup copy must equal the value stored in the database.
row=$(docker exec "$SCRATCH" psql -U $DB_USER -d $DB_NAME -Atc "select sha256||'|'||egnyte_path from documents order by id limit 1")
if [ -n "$row" ]; then
  sha=${row%%|*}; receipt=${row#*|}
  key=${receipt#s3://*/}
  got=$(rclone cat "${DOCS_DST}/${key}" | sha256sum | cut -d' ' -f1)
  [ "$got" = "$sha" ] || { echo "DRILL FAIL: document checksum mismatch" >&2; exit 1; }
  echo "document checksum matches"
else
  echo "no documents in database; document check skipped"
fi
END=$(date +%s)
echo "DRILL PASS: restore $((RESTORED-START))s, total $((END-START))s"
echo "Next (manual): run the audit-chain verify against the restored data as an auditor session."
