#!/bin/sh
set -eu
# Default stays on for the existing single-container setup. The production compose file sets
# RUN_MIGRATIONS=0 and runs a one-shot "migrate" service so API and worker never race.
if [ "${RUN_MIGRATIONS:-1}" = "1" ]; then
  alembic upgrade head
fi
exec "$@"
