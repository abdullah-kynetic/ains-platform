#!/usr/bin/env bash
# Roll back to the image recorded by the last deploy (or one named explicitly).
#   deploy/rollback.sh [image]
# Does not reverse migrations: restore a backup (deploy/backup/restore.sh) if the schema must go back.
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
. "$HERE/lib.sh"
STATE=${KIEN_STATE_DIR:-/opt/kien/releases}
image=${1:-$(cat "$STATE/previous-image" 2>/dev/null || true)}
[ -n "$image" ] || { echo "no previous image recorded; pass one" >&2; exit 2; }
docker image inspect "$image" >/dev/null || { echo "image $image not present" >&2; exit 2; }
sed -i "s#^KIEN_IMAGE=.*#KIEN_IMAGE=$image#" "$KIEN_ENV_FILE"
kien_compose up -d --wait --no-deps api worker
"$HERE/ops/healthcheck.sh"
echo "rollback ok: $image"
