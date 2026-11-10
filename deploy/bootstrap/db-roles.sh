#!/usr/bin/env bash
# Create or update the least-privilege DB roles inside the running postgres container.
# Passwords are read from /etc/kien/db-roles.env (root, mode 600) and passed via the environment;
# nothing is printed. Idempotent: safe to re-run after migrations to refresh grants.
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
. "$HERE/../lib.sh"
ROLES_ENV=${KIEN_DB_ROLES_ENV:-/etc/kien/db-roles.env}
set -a; . "$ROLES_ENV"; set +a
: "${KIEN_MIGRATOR_PASSWORD:?}" "${KIEN_APP_PASSWORD:?}" "${KIEN_BACKUP_PASSWORD:?}"
kien_compose exec -T \
  -e KIEN_MIGRATOR_PASSWORD -e KIEN_APP_PASSWORD -e KIEN_BACKUP_PASSWORD \
  postgres sh -c 'psql -q -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f -' \
  < "$HERE/db-roles.sql"
echo "db roles ok"
