"""Firm-scoped S3 storage; retention is explicit and only for human-finalized reports."""

import asyncio
import re
from datetime import UTC, datetime, timedelta

import boto3
from botocore.config import Config

from app.config import Settings


class S3Storage:
    def __init__(self, settings: Settings):
        if not settings.s3_bucket:
            raise ValueError("S3 storage is not configured")
        self.settings = settings
        self.client = boto3.client(
            "s3", region_name=settings.aws_region, config=Config(signature_version="s3v4")
        )

    @staticmethod
    def key(firm_id: str, path: str) -> str:
        if not re.fullmatch(r"[A-Za-z0-9_-]+", firm_id):
            raise ValueError("Invalid firm identifier")
        if not path or any(p in {"", ".", ".."} for p in path.split("/")) or "\\" in path:
            raise ValueError("Invalid object path")
        return f"firms/{firm_id}/{path}"

    def encryption(self) -> dict:
        params = {"ServerSideEncryption": self.settings.s3_sse}
        if self.settings.s3_sse == "aws:kms":
            if not self.settings.s3_kms_key_id:
                raise ValueError("KMS key is required")
            params["SSEKMSKeyId"] = self.settings.s3_kms_key_id
        return params

    def put(self, firm_id: str, path: str, content: bytes, *, final_report=False) -> dict:
        params = self.encryption()
        if final_report and self.settings.s3_retention_days:
            params.update(
                ObjectLockMode=self.settings.s3_retention_mode,
                ObjectLockRetainUntilDate=datetime.now(UTC)
                + timedelta(days=self.settings.s3_retention_days),
            )
        return self.client.put_object(
            Bucket=self.settings.s3_bucket,
            Key=self.key(firm_id, path),
            Body=content,
            ChecksumAlgorithm="SHA256",
            **params,
        )

    def presign(self, firm_id: str, path: str, *, upload=False, expires=300) -> str:
        if not 1 <= expires <= 900:
            raise ValueError("URL expiry must be 1–900 seconds")
        params = {"Bucket": self.settings.s3_bucket, "Key": self.key(firm_id, path)}
        if upload:
            params.update(self.encryption())
        return self.client.generate_presigned_url(
            "put_object" if upload else "get_object", Params=params, ExpiresIn=expires
        )

    async def download_file(self, path: str) -> bytes:
        # Stored receipt includes bucket, preventing accidental reads after a bucket switch.
        prefix = f"s3://{self.settings.s3_bucket}/"
        if not path.startswith(prefix):
            raise ValueError("Unexpected storage receipt")
        key = path[len(prefix) :]
        parts = key.split("/", 2)
        if len(parts) != 3 or parts[0] != "firms":
            raise ValueError("Invalid storage receipt")
        self.key(parts[1], parts[2])

        def read():
            return self.client.get_object(Bucket=self.settings.s3_bucket, Key=key)["Body"].read()

        return await asyncio.to_thread(read)

    async def aclose(self):
        self.client.close()
