#!/usr/bin/env bash
# Nightly: encrypted Postgres dump + config snapshot into the locked R2 backup bucket via restic.
# Runs from a host systemd timer so a broken app container cannot stop backups.
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
. "$HERE/../lib.sh"
set -a
. "${RESTIC_ENV_FILE:-/etc/kien/restic.env}"
set +a

trap 'ping_url "${HEALTHCHECK_PING_URL:-}" "/fail"; echo "backup FAILED" >&2' ERR

# POSTGRES_USER/DB come from the container's own environment, so no secrets are read here.
kien_compose exec -T postgres sh -c 'pg_dump -U "$POSTGRES_USER" -Fc "$POSTGRES_DB"' \
  | restic backup --stdin --stdin-filename kien-db.dump --tag db

# Config snapshot includes /etc/kien (secrets); the restic repository is encrypted client-side.
restic backup /opt/kien/deploy /etc/kien --tag config

restic forget --tag db --keep-daily "${KEEP_DAILY:-14}" --keep-weekly "${KEEP_WEEKLY:-8}" \
  --keep-monthly "${KEEP_MONTHLY:-6}"

# Weekly prune (Sunday). Locked packs may refuse deletion (HTTP 409); that is tolerated.
if [ "$(date +%u)" = "7" ]; then
  restic prune --max-unused 5% || echo "warning: prune incomplete (locked packs?)" >&2
fi

ping_url "${HEALTHCHECK_PING_URL:-}"
echo "backup ok"
