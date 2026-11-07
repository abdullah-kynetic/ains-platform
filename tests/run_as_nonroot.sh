#!/usr/bin/env bash
# Run the test suite as a non-root user. initdb (used by the *_postgres tests to start a
# disposable real PostgreSQL cluster) refuses to run as root, so those tests fail in root sandboxes.
# Usage (as root): tests/run_as_nonroot.sh [pytest args]   Requires PostgreSQL binaries and `uv sync --frozen`.
set -euo pipefail
[ "$(id -u)" = 0 ] || { exec .venv/bin/python -m pytest -q "$@"; }
id pgtest >/dev/null 2>&1 || useradd -m pgtest
work=/tmp/pgt; mkdir -p "$work"; rm -rf "$work/repo"; cp -a . "$work/repo"; chown -R pgtest "$work"
[ -r "${SSL_CERT_FILE:-/nonexistent}" ] && cp "$SSL_CERT_FILE" "$work/ca.crt" && chmod a+r "$work/ca.crt"
su pgtest -c "cd $work/repo && export TMPDIR=$work; [ -f $work/ca.crt ] && export SSL_CERT_FILE=$work/ca.crt REQUESTS_CA_BUNDLE=$work/ca.crt; unset HTTPS_PROXY HTTP_PROXY https_proxy http_proxy; .venv/bin/python -m pytest -q -p no:cacheprovider $*"
