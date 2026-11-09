#!/usr/bin/env bash
# Alert when any compose service is unhealthy, restarting or not running. No payloads.
set -uo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
. "$HERE/../lib.sh"
bad=0
for svc in postgres api worker caddy; do
  id=$(kien_compose ps -q "$svc" 2>/dev/null | head -n1)
  if [ -z "$id" ]; then alert page "service $svc not running"; bad=1; continue; fi
  state=$(docker inspect -f '{{.State.Status}}/{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}/{{.State.Restarting}}' "$id")
  case "$state" in running/healthy/false | running/none/false) ;; *) alert page "service $svc state $state"; bad=1 ;; esac
done
exit $bad
