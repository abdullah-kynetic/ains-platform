"""Manual R2 smoke test. SYNTHETIC DATA ONLY, against a scratch bucket.

Reads S3_PROVIDER/S3_ENDPOINT_URL/S3_BUCKET/AWS_REGION and the standard AWS_* credential
variables from the environment (never printed). Requires --i-am-using-a-scratch-bucket.
Optional --locked-prefix <prefix>: expects the bucket lock rule on that prefix to make
overwrite and delete fail (HTTP 409).
"""

import argparse
import sys
import urllib.error
import urllib.request
import uuid

from botocore.exceptions import ClientError

from app.config import Settings
from app.storage.s3 import S3Storage

results: list[tuple[str, bool, str]] = []


def check(name: str, fn) -> None:
    try:
        results.append((name, True, str(fn() or "")))
    except Exception as exc:  # noqa: BLE001 - report every failure, never abort the run
        results.append((name, False, f"{type(exc).__name__}: {exc}"[:200]))


def http(method: str, url: str, data: bytes | None = None) -> int:
    req = urllib.request.Request(url, data=data, method=method)
    try:
        with urllib.request.urlopen(req, timeout=20) as r:  # noqa: S310
            return r.status
    except urllib.error.HTTPError as e:
        return e.code


def expect_409(fn) -> str:
    try:
        fn()
    except ClientError as e:
        code = e.response["ResponseMetadata"]["HTTPStatusCode"]
        assert code == 409, f"expected 409, got {code}"
        return "409"
    raise AssertionError("operation succeeded; expected 409")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--i-am-using-a-scratch-bucket", action="store_true", required=True)
    ap.add_argument("--locked-prefix", help="path under firms/<firm>/ covered by a lock rule")
    args = ap.parse_args()
    settings = Settings(_env_file=None)
    store = S3Storage(settings)
    firm, run = "smoke-firm", uuid.uuid4().hex[:8]
    path = f"smoke/{run}.txt"
    key = store.key(firm, path)
    body = b"synthetic smoke test"
    c, bucket = store.client, settings.s3_bucket

    check("put", lambda: store.put(firm, path, body))
    check("head", lambda: c.head_object(Bucket=bucket, Key=key)["ContentLength"] == len(body))
    check("get", lambda: c.get_object(Bucket=bucket, Key=key)["Body"].read() == body)
    check("presign get", lambda: http("GET", store.presign(firm, path)) == 200)
    put_path = f"smoke/{run}-presigned.txt"
    check("presign put", lambda: http("PUT", store.presign(firm, put_path, upload=True), b"x"))
    check("overwrite", lambda: store.put(firm, path, b"synthetic v2"))
    check("delete", lambda: c.delete_object(Bucket=bucket, Key=key))
    check("delete presigned", lambda: c.delete_object(Bucket=bucket, Key=store.key(firm, put_path)))
    if args.locked_prefix:
        locked = f"{args.locked_prefix.strip('/')}/{run}.txt"
        check("locked put", lambda: store.put(firm, locked, body, final_report=True))
        check(
            "locked overwrite -> 409",
            lambda: expect_409(lambda: store.put(firm, locked, b"changed", final_report=True)),
        )
        check(
            "locked delete -> 409",
            lambda: expect_409(lambda: c.delete_object(Bucket=bucket, Key=store.key(firm, locked))),
        )
    for name, ok, detail in results:
        print(f"{'PASS' if ok else 'FAIL'}  {name}  {detail if not ok else ''}".rstrip())
    return 0 if all(ok for _, ok, _ in results) else 1


if __name__ == "__main__":
    sys.exit(main())
