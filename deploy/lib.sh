# Shared helpers, sourced by backup and ops scripts. No secrets are printed.
# Names only: HEALTHCHECK_PING_URL (Healthchecks.io style: success ping, "/fail" on failure).

KIEN_COMPOSE_FILE=${KIEN_COMPOSE_FILE:-/opt/kien/deploy/docker-compose.prod.yml}
KIEN_ENV_FILE=${KIEN_ENV_FILE:-/etc/kien/kien.env}

kien_compose() {
  docker compose -p kien --env-file "$KIEN_ENV_FILE" -f "$KIEN_COMPOSE_FILE" "$@"
}

ping_url() { # $1 = base URL (may be empty), $2 = optional suffix
  [ -n "${1:-}" ] || return 0
  curl -fsS -m 10 -o /dev/null "$1${2:-}" || echo "warning: ping failed" >&2
}

alert() { # $1 = level (warn|page), $2 = short message with no payloads or secrets
  echo "ALERT[$1] $2" >&2
  ping_url "${ALERT_PING_URL:-}" "/fail"
  logger -t kien-alert "$1: $2" 2>/dev/null || true
}
