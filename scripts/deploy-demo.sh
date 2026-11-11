#!/usr/bin/env bash
# Ready-to-run deploy for the demo VPS. Run ON the server, in /opt/kien, as the user that runs docker.
# Written from deploy/docker-compose.prod.yml, deploy/lib.sh and docs/kb/10-sop-deploy-rollback.md.
# NOT RUN by the author: no server access was available. Read it, then run it step by step.
#
#   scripts/deploy-demo.sh backup                         validated database dump, mode 600
#   scripts/deploy-demo.sh deploy  ghcr.io/...@sha256:..  backup, write rollback file, deploy, health check
#   scripts/deploy-demo.sh seed                           synthetic demo practice, credentials to a 600 file
#   scripts/deploy-demo.sh rollback /opt/kien/rollback-<tag>.env
#
# It changes no DNS, no compose file and no memory limit, and prints no secret. Passwords go only
# into the credentials file. Do not point `seed` at a database that holds real data (it refuses).
set -Eeuo pipefail
umask 077
cd "${KIEN_DIR:-/opt/kien}"
. deploy/lib.sh # kien_compose: docker compose -p kien --env-file /etc/kien/kien.env -f deploy/docker-compose.prod.yml
TAG=${KIEN_TAG:-$(date +%Y%m%d%H%M%S)}

health() { # the API container's own health endpoint, then the public one if API_HOST is known
  for _ in $(seq 1 30); do
    if kien_compose exec -T api python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4).status == 200 else 1)" 2>/dev/null; then
      echo "health: api ok"; return 0
    fi
    sleep 3
  done
  echo "health: api did NOT become healthy" >&2; return 1
}

backup() {
  local out="/opt/kien/kien-db-$TAG.dump"
  kien_compose exec -T postgres sh -c 'pg_dump -U "$POSTGRES_USER" -Fc "$POSTGRES_DB"' > "$out"
  [ -s "$out" ] || { echo "empty dump" >&2; rm -f "$out"; return 1; }
  kien_compose exec -T postgres pg_restore --list < "$out" | grep -q "TABLE DATA" \
    || { echo "dump has no table data" >&2; return 1; }
  chmod 600 "$out"
  echo "backup ok: $out"
}

case "${1:-}" in
  backup) backup ;;
  deploy)
    image=${2:?usage: deploy ghcr.io/abdullah-kynetic/ains-platform@sha256:<digest from the Image workflow>}
    case "$image" in *@sha256:*) ;; *) echo "deploy by digest only" >&2; exit 2 ;; esac
    backup
    # Rollback file: the image the API runs right now.
    previous=$(docker inspect --format '{{.Config.Image}}' "$(kien_compose ps -q api)")
    printf 'KIEN_IMAGE=%s\n' "$previous" > "/opt/kien/rollback-$TAG.env"
    chmod 600 "/opt/kien/rollback-$TAG.env"
    echo "rollback file ready: /opt/kien/rollback-$TAG.env (previous image recorded)"
    export KIEN_IMAGE=$image
    kien_compose pull api migrate worker
    kien_compose up -d --no-deps migrate api worker # migrate runs alembic upgrade head first
    health
    echo "deployed $image; to roll back: scripts/deploy-demo.sh rollback /opt/kien/rollback-$TAG.env"
    ;;
  seed)
    set -o noclobber # never overwrite an earlier credentials file
    file="/opt/kien/demo-credentials-$TAG.txt"
    kien_compose run --rm -T --no-deps api \
      python -m app.demo_practice_seed --confirm-synthetic-demo --credentials-file - > "$file"
    chmod 600 "$file"
    echo "seeded. Credentials are in $file (mode 600). Open it on the server; do not paste it anywhere."
    ;;
  rollback)
    file=${2:?usage: rollback /opt/kien/rollback-<tag>.env}
    # shellcheck disable=SC1090
    . "$file"
    : "${KIEN_IMAGE:?rollback file has no KIEN_IMAGE}"
    export KIEN_IMAGE
    kien_compose up -d --no-deps --no-build api worker
    health
    echo "rolled back to $KIEN_IMAGE (images only; migrations are additive so the old image runs on the new schema)"
    ;;
  *) echo "usage: scripts/deploy-demo.sh backup|deploy <image@digest>|seed|rollback <file>" >&2; exit 2 ;;
esac
