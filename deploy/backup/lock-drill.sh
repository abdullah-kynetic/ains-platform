#!/usr/bin/env bash
# Bucket-lock drill (plan section 6.1 + coordinator note). MANUAL, needs Abdullah's R2 backup token
# and a bucket with the lock rules applied. Synthetic data only. Prints PASS/FAIL per step.
# Env: RESTIC_REPOSITORY, RESTIC_PASSWORD_FILE, AWS_* (backup token); RCLONE_CONFIG with remotes
#      DRILL_SRC (a scratch source bucket/dir) and DRILL_DST (the locked docs backup bucket/prefix).
# Use a scratch prefix such as "lock-drill/" that the lock rule covers. Locked objects stay until
# the lock expires, so keep the drill small.
set -uo pipefail
: "${DRILL_SRC:?remote:path with synthetic files}" "${DRILL_DST:?locked remote:path/prefix}"
fail=0
step() { # name, expected-rc (0 = must succeed, 1 = must fail), command...
  local name=$1 want=$2; shift 2
  "$@" >/dev/null 2>&1; local rc=$?
  if { [ "$want" = 0 ] && [ $rc -eq 0 ]; } || { [ "$want" = 1 ] && [ $rc -ne 0 ]; }; then echo "PASS $name"
  else echo "FAIL $name (rc=$rc)"; fail=1; fi
}
WORK=$(mktemp -d); trap 'rm -rf "$WORK"' EXIT
mkdir "$WORK/src"; echo "synthetic one $(date +%s)" > "$WORK/src/a.txt"

echo "== rclone copy --immutable --checksum into the locked prefix =="
step "rclone: first copy succeeds" 0 rclone copy "$WORK/src" "$DRILL_DST" --immutable --checksum
step "rclone: identical re-copy succeeds (no rewrite)" 0 rclone copy "$WORK/src" "$DRILL_DST" --immutable --checksum
echo "changed $(date +%s)" > "$WORK/src/a.txt"
step "rclone: changed source is refused, not overwritten" 1 rclone copy "$WORK/src" "$DRILL_DST" --immutable --checksum
step "rclone: delete of locked object is refused (409)" 1 rclone deletefile "$DRILL_DST/a.txt"

echo "== restic against the locked layout =="
step "restic: init or open repository" 0 sh -c 'restic cat config >/dev/null 2>&1 || restic init'
echo "synthetic restic" | restic backup --stdin --stdin-filename drill.txt --tag drill >/dev/null 2>&1
step "restic: backup succeeds" 0 sh -c 'echo synthetic | restic backup --stdin --stdin-filename drill.txt --tag drill'
step "restic: check passes" 0 restic check
step "restic: forget works" 0 restic forget --tag drill --keep-last 1
step "restic: prune tolerated (may warn on locked packs)" 0 sh -c 'restic prune --max-unused 5% || true'
step "restic: restore still works after prune" 0 sh -c 'restic dump latest drill.txt --tag drill'

[ $fail -eq 0 ] && echo "LOCK DRILL PASS" || { echo "LOCK DRILL FAIL: use the pg_dump | age fallback (plan 6.1)"; exit 1; }
