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
cleanup() { docker rm -f "$SCRATCH" >/dev/null 2>&1 || true; }
trap cleanup EXIT
cleanup
docker run -d --name "$SCRATCH" -e POSTGRES_USER=$DB_USER -e POSTGRES_PASSWORD="$(head -c 24 /dev/urandom | base64)" \
  -e POSTGRES_DB=$DB_NAME --network none postgres:16 >/dev/null
for _ in $(seq 1 30); do docker exec "$SCRATCH" pg_isready -U $DB_USER -d $DB_NAME >/dev/null 2>&1 && break; sleep 1; done

"$HERE/restore.sh" latest "$SCRATCH" $DB_USER $DB_NAME
RESTORED=$(date +%s)

COUNT_SQL="select table_name||'='||(xpath('/row/c/text()', query_to_xml('select count(*) c from public.'||quote_ident(table_name), false, true, '')))[1]::text from information_schema.tables where table_schema='public' and table_type='BASE TABLE' order by 1"
src=$(kien_compose exec -T postgres sh -c "psql -U \"\$POSTGRES_USER\" -d \"\$POSTGRES_DB\" -Atc \"$COUNT_SQL\"")
dst=$(docker exec "$SCRATCH" psql -U $DB_USER -d $DB_NAME -Atc "$COUNT_SQL")
if [ "$src" != "$dst" ]; then
  echo "DRILL FAIL: row counts differ (backup may predate recent writes)" >&2
  diff <(echo "$src") <(echo "$dst") >&2 || true
  exit 1
fi
echo "row counts match for $(echo "$src" | wc -l) tables"

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
