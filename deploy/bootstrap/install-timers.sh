#!/usr/bin/env bash
# Install the backup, docs-sync, docs-check and alert systemd timers from deploy/systemd. Run as root.
set -euo pipefail
HERE=$(cd "$(dirname "$0")/.." && pwd)
[ "$(id -u)" = 0 ] || { echo "run as root" >&2; exit 2; }
install -m 644 "$HERE"/systemd/*.service "$HERE"/systemd/*.timer /etc/systemd/system/
systemctl daemon-reload
for t in "$HERE"/systemd/*.timer; do
  systemctl enable --now "$(basename "$t")"
done
systemctl list-timers 'kien-*' --no-pager
