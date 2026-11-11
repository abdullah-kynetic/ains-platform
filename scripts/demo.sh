#!/usr/bin/env bash
# Synthetic demo of one complete audit on the real backend. See DEMO.md.
#
#   scripts/demo.sh test    run steps 1 to 7 in a browser, headless, from a clean database
#   scripts/demo.sh serve   start a clean seeded backend and web app to click through by hand
#
# Synthetic data only. The database is a throwaway SQLite file, deleted at every start.
# Refuses to run if DATABASE_URL points at Postgres. Does not touch deploy/ or compose files.
set -euo pipefail
cd "$(dirname "$0")/.."

case "${DATABASE_URL:-}" in *postgres*) echo "Refusing: DATABASE_URL points at Postgres. This demo is synthetic-only." >&2; exit 1;; esac

mode="${1:-test}"
case "$mode" in
  test)
    cd web
    exec npm run test:e2e:live -- --trace off e2e-live/demo-journey-live.spec.ts
    ;;
  serve)
    export PYTHONPATH=.
    .venv/bin/python scripts/e2e_backend.py --port 8000 --db /tmp/kien-demo.db &
    api=$!
    trap 'kill $api 2>/dev/null || true' EXIT
    for _ in $(seq 1 60); do curl -fs http://127.0.0.1:8000/health >/dev/null && break; sleep 1; done
    echo "Auditor:  http://kynetic.localhost:3100/sign-in"
    echo "Client portals appear as http://<portal-name>.localhost:3100 once a workspace is created."
    cd web
    NEXT_PUBLIC_USE_MOCKS= NEXT_PUBLIC_API_URL='http://{portal}:8000' npm run dev -- --hostname 0.0.0.0 --port 3100
    ;;
  *) echo "usage: scripts/demo.sh test|serve" >&2; exit 2;;
esac
