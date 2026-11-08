#!/usr/bin/env bash
# Daily: copy (never sync) documents to the locked backup bucket. --immutable fails loudly if an
# existing object would be altered. "check" mode compares counts and sizes (weekly timer).
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
. "$HERE/../lib.sh"
set -a
. "${RESTIC_ENV_FILE:-/etc/kien/restic.env}"
set +a
export RCLONE_CONFIG=${RCLONE_CONFIG:-/etc/kien/rclone.conf}
MODE=${1:-copy}

trap 'ping_url "${DOCS_PING_URL:-}" "/fail"; echo "docs-sync FAILED" >&2' ERR

case "$MODE" in
  copy) rclone copy "$DOCS_SRC" "$DOCS_DST" --immutable --checksum ;;
  check) rclone check "$DOCS_SRC" "$DOCS_DST" --one-way --size-only ;;
  *) echo "usage: docs-sync.sh [copy|check]" >&2; exit 2 ;;
esac
ping_url "${DOCS_PING_URL:-}"
echo "docs-sync $MODE ok"
