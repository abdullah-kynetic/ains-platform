#!/usr/bin/env bash
# Checkout starts at canonical main with complete history. Only a commit already
# on that history may be built using the package-write token.
set -euo pipefail
[[ ${BUILD_SHA:-} =~ ^[0-9a-f]{40}$ ]] || { echo 'Invalid image commit' >&2; exit 2; }
git merge-base --is-ancestor "$BUILD_SHA" refs/remotes/origin/main || {
  echo 'Image commit is not on trusted main' >&2
  exit 3
}
git checkout --quiet --detach "$BUILD_SHA"
