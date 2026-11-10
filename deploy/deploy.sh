#!/usr/bin/env bash
# Deploy one image to the single Kien environment.
#   deploy/deploy.sh kien-api:sha-<12>
# Steps: pre-checks -> backup if a migration is pending -> save previous image -> up postgres clamav
# -> db roles -> run --rm migrate -> up api worker caddy (ai-adapter only with KIEN_AI=1) ->
# healthcheck -> print the RELEASES.md row. Prints no secrets.
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
. "$HERE/lib.sh"
image=${1:?usage: deploy.sh <image>}
STATE=${KIEN_STATE_DIR:-/opt/kien/releases}

# Pre-checks
for f in "$KIEN_ENV_FILE" /etc/kien/postgres.env /etc/kien/migrate.env /etc/kien/app.env; do
  [ -f "$f" ] || { echo "missing $f" >&2; exit 2; }
  [ "$(stat -c %a "$f")" = 600 ] || { echo "$f must be mode 600" >&2; exit 2; }
done
docker image inspect "$image" >/dev/null || { echo "image $image not present (build-on-host.sh)" >&2; exit 2; }
avail=$(df --output=avail -k / | tail -1)
[ "$avail" -gt 2000000 ] || { echo "less than 2 GB disk free" >&2; exit 2; }

prev=$(grep -E '^KIEN_IMAGE=' "$KIEN_ENV_FILE" | cut -d= -f2- || true)
mkdir -p "$STATE"
[ -n "$prev" ] && echo "$prev" > "$STATE/previous-image"
sed -i "s#^KIEN_IMAGE=.*#KIEN_IMAGE=$image#" "$KIEN_ENV_FILE"
grep -q '^KIEN_IMAGE=' "$KIEN_ENV_FILE" || echo "KIEN_IMAGE=$image" >> "$KIEN_ENV_FILE"

kien_compose up -d --wait postgres
[ -f /etc/kien/db-roles.env ] && "$HERE/bootstrap/db-roles.sh"

# Backup first if this image carries a migration the database has not run yet.
pending=0
if kien_compose exec -T postgres sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "select 1 from alembic_version"' >/dev/null 2>&1; then
  current=$(kien_compose exec -T postgres sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "select version_num from alembic_version"')
  heads=$(docker run --rm --network none "$image" alembic heads 2>/dev/null | awk '{print $1}')
  [ "$current" = "$heads" ] || pending=1
fi
if [ "$pending" = 1 ] && [ -f /etc/kien/restic.env ]; then
  "$HERE/backup/backup.sh"
fi

kien_compose up -d clamav
kien_compose run --rm migrate
[ -f /etc/kien/db-roles.env ] && "$HERE/bootstrap/db-roles.sh" # grants for any new tables
services=(api worker caddy)
profile=()
[ "${KIEN_AI:-0}" = 1 ] && { profile=(--profile ai); services+=(ai-adapter); }
kien_compose "${profile[@]}" up -d --wait "${services[@]}"
"$HERE/ops/healthcheck.sh"

rev=$(docker image inspect -f '{{index .Config.Labels "org.opencontainers.image.revision"}}' "$image" 2>/dev/null || true)
id=$(docker image inspect -f '{{.Id}}' "$image")
echo "deploy ok"
echo "RELEASES row: | $(date -u +%Y-%m-%d) | ${rev:0:12} | $id | kien VPS (single env) | deploy.sh |"
