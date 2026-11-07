#!/usr/bin/env bash
# Nightly: encrypted Postgres dump + config snapshot into the locked R2 backup bucket via restic.
# Runs from a host systemd timer so a broken app container cannot stop backups.
set -Eeuo pipefail # -E: the ERR trap must also fire inside functions
HERE=$(cd "$(dirname "$0")" && pwd)
. "$HERE/../lib.sh"
set -a
. "${RESTIC_ENV_FILE:-/etc/kien/restic.env}"
set +a

# Counts SQL (table=rows). Recorded before and after the dump so the restore drill can compare
# against the state at backup time instead of the live database.
COUNT_SQL="select table_name||'='||(xpath('/row/c/text()', query_to_xml('select count(*) c from public.'||quote_ident(table_name), false, true, '')))[1]::text from information_schema.tables where table_schema='public' and table_type='BASE TABLE' order by 1"
count_rows() {
  kien_compose exec -T postgres sh -c "psql -U \"\$POSTGRES_USER\" -d \"\$POSTGRES_DB\" -Atc \"$COUNT_SQL\""
}

# Dump to a work file first and validate it BEFORE restic sees it, so a dump that dies mid-stream
# can never become a snapshot tagged "db".
WORK=${KIEN_BACKUP_WORK:-/var/backups/kien-work} # fixed path so snapshots dedupe and restores can name files
case "$WORK" in /var/backups/* | /var/tmp/* | /tmp/*) ;; *) echo "unsafe work dir" >&2; exit 2 ;; esac
rm -rf "$WORK"
mkdir -p -m 700 "$WORK"
trap 'rm -rf "$WORK"; ping_url "${HEALTHCHECK_PING_URL:-}" "/fail"; echo "backup FAILED" >&2' ERR
trap 'rm -rf "$WORK"' EXIT
chmod 700 "$WORK"
count_rows > "$WORK/kien-db.counts.before"
# POSTGRES_USER/DB come from the container's own environment, so no secrets are read here.
kien_compose exec -T postgres sh -c 'pg_dump -U "$POSTGRES_USER" -Fc "$POSTGRES_DB"' > "$WORK/kien-db.dump"
[ -s "$WORK/kien-db.dump" ] || { echo "empty dump" >&2; false; }
kien_compose exec -T postgres pg_restore --list < "$WORK/kien-db.dump" > "$WORK/kien-db.toc"
grep -q "TABLE DATA" "$WORK/kien-db.toc" || { echo "dump has no table data" >&2; false; }
count_rows > "$WORK/kien-db.counts.after"
restic backup "$WORK/kien-db.dump" "$WORK/kien-db.counts.before" "$WORK/kien-db.counts.after" \
  --tag db --tag validated

# Config snapshot includes /etc/kien (secrets); the restic repository is encrypted client-side.
restic backup /opt/kien/deploy /etc/kien --tag config

restic forget --tag config --keep-daily "${KEEP_CONFIG_DAILY:-7}" --keep-weekly "${KEEP_CONFIG_WEEKLY:-4}" \
  --keep-monthly "${KEEP_CONFIG_MONTHLY:-3}"
restic forget --tag db --keep-daily "${KEEP_DAILY:-14}" --keep-weekly "${KEEP_WEEKLY:-8}" \
  --keep-monthly "${KEEP_MONTHLY:-6}"

# Weekly prune (Sunday). Locked packs may refuse deletion (HTTP 409); that is tolerated.
if [ "$(date +%u)" = "7" ]; then
  restic prune --max-unused 5% || echo "warning: prune incomplete (locked packs?)" >&2
fi

ping_url "${HEALTHCHECK_PING_URL:-}"
echo "backup ok"
