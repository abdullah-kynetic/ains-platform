#!/usr/bin/env bash
# Restore a database dump from restic into a Postgres container.
# usage: restore.sh <snapshot-id|latest> <container> <db-user> <db-name>
# Needs RESTIC_REPOSITORY and RESTIC_PASSWORD_FILE plus a (read-only) token in the environment.
# --no-privileges: the scratch cluster has no kien_app/kien_backup roles; grants are re-applied by
# deploy/bootstrap/db-roles.sh on a real restore.
# Never restores into the live "kien" project; refuses container names containing "kien-postgres".
set -euo pipefail
SNAP=${1:?snapshot id or latest}; CONTAINER=${2:?target container}
DB_USER=${3:?db user}; DB_NAME=${4:?db name}
case "$CONTAINER" in *kien-postgres*) echo "refusing to restore into the live database" >&2; exit 3 ;; esac
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
WORK=${KIEN_BACKUP_WORK:-/var/backups/kien-work}
# Only snapshots that passed validation at backup time carry the "validated" tag.
restic dump "$SNAP" "$WORK/kien-db.dump" --tag db,validated > "$TMP/kien-db.dump"
docker cp "$TMP/kien-db.dump" "$CONTAINER:/tmp/kien-db.dump"
docker exec "$CONTAINER" pg_restore -U "$DB_USER" -d "$DB_NAME" --no-owner --no-privileges --exit-on-error /tmp/kien-db.dump
docker exec "$CONTAINER" rm -f /tmp/kien-db.dump
echo "restored $SNAP into $CONTAINER"
