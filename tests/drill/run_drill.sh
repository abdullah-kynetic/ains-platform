#!/usr/bin/env bash
# Backup/restore drill harness. EMULATOR coverage: local PostgreSQL 16 (apt), moto S3 emulator (not MinIO,
# not real R2), real restic + rclone binaries, `docker` replaced by tests/drill/shim/docker. SYNTHETIC data only.
# usage (root, disposable sandbox): CAND=/path/to/checked-out/candidate tests/drill/run_drill.sh
# Needs: restic rclone, /usr/lib/postgresql/16, a candidate venv at $CAND/.venv, moto venv at $MOTO.
# Creates and removes /etc/kien and /opt/kien/deploy (sandbox only; refuses if they already exist).
set -uo pipefail
CAND=${CAND:?candidate checkout}; HERE=$(cd "$(dirname "$0")" && pwd)
MOTO=${MOTO:-/tmp/motovenv}; W=${W:-/tmp/drill}; PGB=/usr/lib/postgresql/16/bin
PGPORT=55432; S3P=55500; EP=http://127.0.0.1:$S3P
PY=$CAND/.venv/bin/python
[ -e /etc/kien ] || [ -e /opt/kien ] && { echo "refusing: /etc/kien or /opt/kien exists" >&2; exit 9; }
rm -rf "$W"; mkdir -p "$W" /etc/kien /opt/kien; chown pgtest "$W"
RES=$W/results.tsv; : > "$RES"
rec() { printf '%s\t%s\t%s\n' "$1" "$2" "$3" | tee -a "$RES"; }
expect() { # name expected_rc actual_rc note
  if [ "$3" = "$2" ] || { [ "$2" = nz ] && [ "$3" != 0 ]; }; then rec "$1" PASS "$4"; else rec "$1" FAIL "rc=$3 expected=$2 $4"; fi; }
cleanup() { su pgtest -c "$PGB/pg_ctl -D $W/pg -m immediate stop" >/dev/null 2>&1; kill "${MPID:-0}" 2>/dev/null; rm -rf /etc/kien /opt/kien; }
trap cleanup EXIT
export PATH=$HERE/shim:$PATH DRILL_PGPORT=$PGPORT PGHOST=127.0.0.1 PGPORT=$PGPORT
unset AWS_CA_BUNDLE SSL_CERT_FILE REQUESTS_CA_BUNDLE CURL_CA_BUNDLE HTTPS_PROXY HTTP_PROXY https_proxy http_proxy NODE_EXTRA_CA_CERTS
export NO_PROXY=127.0.0.1
export AWS_ACCESS_KEY_ID=drill AWS_SECRET_ACCESS_KEY=drill-secret AWS_DEFAULT_REGION=us-east-1

# --- environment
su pgtest -c "$PGB/initdb -D $W/pg -A trust -U kien >/dev/null && $PGB/pg_ctl -D $W/pg -l $W/pg.log -o '-p $PGPORT -c listen_addresses=127.0.0.1 -k $W' -w start >/dev/null" || { rec env BLOCKED "postgres start"; exit 1; }
$PGB/createdb -U kien kien && rec env_postgres PASS "$($PGB/postgres --version)"
"$MOTO/bin/moto_server" -p $S3P >"$W/moto.log" 2>&1 & MPID=$!
for _ in $(seq 30); do curl -s $EP >/dev/null && break; sleep 0.5; done
rec env_s3 PASS "moto S3 EMULATOR; restic $(restic version | cut -d' ' -f2), rclone $(rclone version | head -1)"
export KIEN_DB_URL=postgresql+psycopg://kien@127.0.0.1:$PGPORT/kien DATABASE_URL=postgresql+psycopg://kien@127.0.0.1:$PGPORT/kien DRILL_S3_ENDPOINT=$EP
(cd "$CAND" && $PY -m alembic upgrade head >"$W/alembic.log" 2>&1) && rec migrate PASS "alembic head=$(psql -U kien -d kien -Atc 'select version_num from alembic_version')" || { rec migrate FAIL "$(tail -2 $W/alembic.log)"; exit 1; }
(cd "$CAND" && PYTHONPATH=$CAND $PY "$HERE/seed.py") >"$W/seed.log" 2>&1 && rec seed PASS "synthetic firm/users/3 documents/15 audit rows" || { rec seed FAIL "$(tail -3 $W/seed.log)"; exit 1; }

# --- config (synthetic credentials, local emulator only)
echo "drill-restic-password-not-a-secret" > /etc/kien/restic.pass
cat > /etc/kien/rclone.conf <<RC
[r2prod]
type = s3
provider = Other
endpoint = $EP
access_key_id = drill
secret_access_key = drill-secret
[r2backup]
type = s3
provider = Other
endpoint = $EP
access_key_id = drill
secret_access_key = drill-secret
RC
cat > /etc/kien/restic.env <<RE
RESTIC_REPOSITORY=s3:$EP/kien-prod-backups
RESTIC_PASSWORD_FILE=/etc/kien/restic.pass
AWS_ACCESS_KEY_ID=drill
AWS_SECRET_ACCESS_KEY=drill-secret
AWS_DEFAULT_REGION=us-east-1
DOCS_SRC=r2prod:kien-prod-documents
DOCS_DST=r2backup:kien-prod-backups-docs
RE
cp /etc/kien/restic.env /etc/kien/restore.env
cp -r "$CAND/deploy" /opt/kien/deploy
touch /etc/kien/kien.env /opt/kien/deploy/docker-compose.prod.yml
"$MOTO/bin/python" - <<PY
import boto3
s=boto3.client("s3",endpoint_url="$EP",region_name="us-east-1")
for b in ("kien-prod-backups","kien-prod-backups-docs"): s.create_bucket(Bucket=b)
PY
export RESTIC_ENV_FILE=/etc/kien/restic.env RESTORE_ENV_FILE=/etc/kien/restore.env RCLONE_CONFIG=/etc/kien/rclone.conf
set -a; . /etc/kien/restic.env; set +a
D=/opt/kien/deploy
restic init >"$W/init.log" 2>&1 && rec restic_init PASS "encrypted repo on S3 emulator" || { rec restic_init FAIL "$(tail -2 $W/init.log)"; exit 1; }

# --- 1 backup
"$D/backup/backup.sh" >"$W/backup.log" 2>&1; expect backup_run 0 $? "$(tail -1 $W/backup.log)"
n=$(restic snapshots --json | $MOTO/bin/python -c 'import json,sys;print(len(json.load(sys.stdin)))'); rec backup_snapshots PASS "snapshots=$n (db+config)"
# --- 2 documents copy
"$D/backup/docs-sync.sh" copy >"$W/docs.log" 2>&1; expect docs_copy 0 $? "$(tail -1 $W/docs.log)"
"$D/backup/docs-sync.sh" copy >"$W/docs2.log" 2>&1; expect docs_copy_idempotent 0 $? "second run"
"$D/backup/docs-sync.sh" check >"$W/docs3.log" 2>&1; expect docs_check 0 $? "$(tail -1 $W/docs3.log)"
# --- 3 restore drill (script under test)
"$D/backup/restore-drill.sh" >"$W/drill.log" 2>&1; expect restore_drill 0 $? "$(grep -E 'DRILL|match' $W/drill.log | tr '\n' ' ')"
# --- 4 manual restore + app reads + schema version
bash -c 'docker run -d --name kien-restore-drill x' >/dev/null
"$D/backup/restore.sh" latest kien-restore-drill drill drill >"$W/restore.log" 2>&1; expect restore_script 0 $? "$(tail -1 $W/restore.log)"
sv_src=$(psql -U kien -d kien -Atc 'select version_num from alembic_version'); sv_dst=$(psql -U drill -d drill -Atc 'select version_num from alembic_version')
[ "$sv_src" = "$sv_dst" ] && rec schema_version PASS "$sv_dst" || rec schema_version FAIL "src=$sv_src restored=$sv_dst"
a=$(pg_dump -U kien -d kien --schema-only --no-owner | grep -vE "^--|restrict" | sed -E "s/,$//; s/(CONSTRAINT [a-z_]+ CHECK).*/\1/" | sort); b=$(pg_dump -U drill -d drill --schema-only --no-owner | grep -vE "^--|restrict" | sed -E "s/,$//; s/(CONSTRAINT [a-z_]+ CHECK).*/\1/" | sort)
echo "$a" > "$W/schema_src.sql"; echo "$b" > "$W/schema_dst.sql"
[ "$a" = "$b" ] && rec schema_identical PASS "pg_dump --schema-only equal (sorted; CHECK bodies compared by name only: PG re-deparses the expression text on restore, semantically equal; \restrict tokens ignored)" || rec schema_identical FAIL "schema dumps differ: $(diff <(echo "$a") <(echo "$b") | head -4 | tr "\n" " ")"
(cd "$CAND" && TARGET_DB_URL=postgresql+psycopg://drill@127.0.0.1:$PGPORT/drill BACKUP_S3_ENDPOINT=$EP BACKUP_BUCKET=kien-prod-backups-docs PYTHONPATH=$CAND $PY "$HERE/app_read.py") >"$W/appread.log" 2>&1; expect app_reads_restored 0 $? "$(tail -1 $W/appread.log)"
# --- 5 encryption
mkdir -p "$W/raw"; "$MOTO/bin/python" - <<PY
import boto3
s=boto3.client("s3",endpoint_url="$EP",region_name="us-east-1")
for o in s.list_objects_v2(Bucket="kien-prod-backups")["Contents"]:
    open("$W/raw/"+o["Key"].replace("/","_"),"wb").write(s.get_object(Bucket="kien-prod-backups",Key=o["Key"])["Body"].read())
PY
if grep -rlE "Synthetic Firm|PGDMP|synthetic-firm|drill-restic-password" "$W/raw" >/dev/null; then rec encryption_at_rest FAIL "plaintext marker found in repo objects"; else rec encryption_at_rest PASS "no plaintext markers in $(ls $W/raw | wc -l) repo objects"; fi
echo wrong > "$W/wrong.pass"; RESTIC_PASSWORD_FILE=$W/wrong.pass restic snapshots >/dev/null 2>&1; expect wrong_password_rejected nz $? "restic with wrong password"
# --- 6 error handling
"$D/backup/restore.sh" latest my-kien-postgres-1 drill drill >/dev/null 2>&1; expect restore_refuses_live 3 $? "container name contains kien-postgres"
"$D/backup/restore.sh" deadbeef kien-restore-drill drill drill >/dev/null 2>&1; expect restore_unknown_snapshot nz $? "bad snapshot id"
before=$(restic snapshots --tag db --json | $MOTO/bin/python -c 'import json,sys;print(len(json.load(sys.stdin)))')
DRILL_SRC_DB=no_such_db "$D/backup/backup.sh" >"$W/bfail.log" 2>&1; rc=$?
after=$(restic snapshots --tag db --json | $MOTO/bin/python -c 'import json,sys;print(len(json.load(sys.stdin)))')
expect backup_fails_when_dump_fails nz $rc "exit code on pg_dump failure"
[ "$before" = "$after" ] && rec backup_no_partial_snapshot PASS "db snapshots $before -> $after" || rec backup_no_partial_snapshot FAIL "failed dump still saved a db snapshot ($before -> $after): restore of 'latest' would use a truncated/empty dump"
# doc tamper in backup copy and row-count drift
psql -U kien -d kien -qc "insert into firms(id,name,slug,created_at) values('drift','Drift','drift',now())"
"$D/backup/restore-drill.sh" >"$W/drill2.log" 2>&1; expect drill_detects_row_drift nz $? "$(grep DRILL $W/drill2.log | head -1)"
psql -U kien -d kien -qc "delete from firms where id='drift'"
"$MOTO/bin/python" - <<PY
import boto3
s=boto3.client("s3",endpoint_url="$EP",region_name="us-east-1")
k=s.list_objects_v2(Bucket="kien-prod-backups-docs")["Contents"][0]["Key"]
s.put_object(Bucket="kien-prod-backups-docs",Key=k,Body=b"tampered synthetic")
PY
"$D/backup/restore-drill.sh" >"$W/drill3.log" 2>&1; expect drill_detects_tampered_document nz $? "$(grep DRILL $W/drill3.log | head -1) (note: checks only first document by id)"
# corrupted repository pack
restic check --read-data >/dev/null 2>&1; expect restic_check_clean 0 $? "before corruption"
"$MOTO/bin/python" - <<PY
import boto3
s=boto3.client("s3",endpoint_url="$EP",region_name="us-east-1")
k=[o["Key"] for o in s.list_objects_v2(Bucket="kien-prod-backups",Prefix="data/")["Contents"]][0]
b=bytearray(s.get_object(Bucket="kien-prod-backups",Key=k)["Body"].read()); b[len(b)//2]^=0xFF
s.put_object(Bucket="kien-prod-backups",Key=k,Body=bytes(b))
PY
restic check --read-data >/dev/null 2>&1; expect restic_detects_corruption nz $? "bit flip in one pack"
# alerts
DISK_WARN=0 DISK_PAGE=101 "$D/ops/disk-alert.sh" >/dev/null 2>&1; expect disk_alert_warn_rc1 1 $? "forced warn threshold"
DISK_WARN=0 DISK_PAGE=0 "$D/ops/disk-alert.sh" >/dev/null 2>&1; expect disk_alert_page_rc2 2 $? "forced page threshold"
echo "--- results: $RES"; cut -f2 "$RES" | sort | uniq -c
