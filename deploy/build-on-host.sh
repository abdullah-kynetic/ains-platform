#!/usr/bin/env bash
# Build the app image on the VPS from a checked-out commit: kien-api:sha-<first 12 of the SHA>.
#   deploy/build-on-host.sh <full-git-sha>
# Source must already be at /opt/kien/src/<sha> (git archive or clone at exactly that commit).
set -euo pipefail
sha=${1:?usage: build-on-host.sh <git-sha>}
case "$sha" in *[!0-9a-f]* | "") echo "sha must be lowercase hex" >&2; exit 2 ;; esac
[ "${#sha}" -ge 12 ] || { echo "sha too short" >&2; exit 2; }
src=${KIEN_SRC_ROOT:-/opt/kien/src}/$sha
[ -f "$src/Dockerfile" ] || { echo "no Dockerfile in $src" >&2; exit 2; }
tag="kien-api:sha-${sha:0:12}"
docker build --pull -t "$tag" --label "org.opencontainers.image.revision=$sha" "$src"
echo "$tag"
