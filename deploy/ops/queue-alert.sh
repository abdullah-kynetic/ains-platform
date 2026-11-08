#!/usr/bin/env bash
# Read-only check of the document-check queue: oldest queued job or stuck running job over
# 5 minutes, or any failed job. Prints counts and ages only, never document data.
set -uo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
. "$HERE/../lib.sh"
SQL="select
  coalesce(max(case when lower(status)='queued' then extract(epoch from now()-available_at) end),0)::int,
  coalesce(max(case when lower(status)='running' then extract(epoch from now()-started_at) end),0)::int,
  count(*) filter (where lower(status)='failed')
 from check_jobs"
out=$(kien_compose exec -T postgres sh -c "psql -U \"\$POSTGRES_USER\" -d \"\$POSTGRES_DB\" -At -F' ' -c \"$SQL\"") || { alert page "queue check could not query database"; exit 2; }
read -r queued_age running_age failed <<<"$out"
rc=0
[ "${queued_age:-0}" -gt 300 ] && { alert warn "oldest queued job ${queued_age}s"; rc=1; }
[ "${running_age:-0}" -gt 300 ] && { alert warn "running job stuck ${running_age}s"; rc=1; }
[ "${failed:-0}" -gt 0 ] && { alert warn "failed jobs: ${failed}"; rc=1; }
exit $rc
