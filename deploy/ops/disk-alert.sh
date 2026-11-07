#!/usr/bin/env bash
# Warn at 70% and page at 85% disk use on / and /var/lib/docker (when separate).
# Memory/swap/load checks use /proc. Thresholds can be overridden by env for testing.
set -uo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
. "$HERE/../lib.sh"
WARN=${DISK_WARN:-70} PAGE=${DISK_PAGE:-85} DF=${DF_CMD:-df}
rc=0
for path in / /var/lib/docker; do
  [ -d "$path" ] || continue
  pct=$($DF --output=pcent "$path" | tail -n1 | tr -dc '0-9')
  if [ -n "$pct" ] && [ "$pct" -ge "$PAGE" ]; then alert page "disk $path at ${pct}%"; rc=2
  elif [ -n "$pct" ] && [ "$pct" -ge "$WARN" ]; then alert warn "disk $path at ${pct}%"; [ $rc -eq 0 ] && rc=1
  fi
done
# Memory: warn at 75% used, and on any sustained swap use.
mem_total=$(awk '/MemTotal/{print $2}' /proc/meminfo); mem_avail=$(awk '/MemAvailable/{print $2}' /proc/meminfo)
if [ -n "$mem_total" ] && [ $(( (mem_total - mem_avail) * 100 / mem_total )) -ge 75 ]; then alert warn "memory above 75%"; [ $rc -eq 0 ] && rc=1; fi
swap_used=$(awk '/SwapTotal/{t=$2}/SwapFree/{f=$2}END{print t-f}' /proc/meminfo)
if [ "${swap_used:-0}" -gt 51200 ]; then alert warn "swap in use"; [ $rc -eq 0 ] && rc=1; fi
load=$(cut -d' ' -f3 /proc/loadavg)  # 15-minute average
if awk "BEGIN{exit !($load > 1.5)}"; then alert warn "15-minute load above 1.5"; [ $rc -eq 0 ] && rc=1; fi
exit $rc
