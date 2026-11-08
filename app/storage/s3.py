"""Firm-scoped S3 storage; retention is explicit and only for human-finalized reports."""

import asyncio
import hashlib
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
        if settings.s3_provider == "r2":
            if not settings.s3_endpoint_url:
                raise ValueError("S3_ENDPOINT_URL is required for Cloudflare R2")
            # R2 rejects some default CRC checksums sent by recent boto3 versions.
            config = Config(
                signature_version="s3v4",
                s3={"addressing_style": "path"},
                request_checksum_calculation="when_required",
                response_checksum_validation="when_required",
            )
        else:
            config = Config(signature_version="s3v4")
        self.client = boto3.client(
            "s3",
            region_name=settings.aws_region,
            endpoint_url=settings.s3_endpoint_url or None,
            config=config,
        )

    @staticmethod
    def key(firm_id: str, path: str) -> str:
        if not re.fullmatch(r"[A-Za-z0-9_-]+", firm_id):
            raise ValueError("Invalid firm identifier")
        if not path or any(p in {"", ".", ".."} for p in path.split("/")) or "\\" in path:
            raise ValueError("Invalid object path")
        return f"firms/{firm_id}/{path}"

    @property
    def is_r2(self) -> bool:
        return self.settings.s3_provider == "r2"

    def encryption(self) -> dict:
        if self.is_r2:  # R2 encrypts at rest by default and rejects the SSE header.
            return {}
        params = {"ServerSideEncryption": self.settings.s3_sse}
        if self.settings.s3_sse == "aws:kms":
            if not self.settings.s3_kms_key_id:
                raise ValueError("KMS key is required")
            params["SSEKMSKeyId"] = self.settings.s3_kms_key_id
        return params

    def put(self, firm_id: str, path: str, content: bytes, *, final_report=False) -> dict:
        params = self.encryption()
        if self.is_r2:
            # No S3 Object Lock or S3 checksum on R2: retention is a bucket lock rule on
            # the final-report prefix; integrity is the app's own SHA-256, kept as metadata.
            params["Metadata"] = {"sha256": hashlib.sha256(content).hexdigest()}
            checksum: dict = {}
        else:
            checksum = {"ChecksumAlgorithm": "SHA256"}
        if final_report and self.settings.s3_retention_days and not self.is_r2:
            params.update(
                ObjectLockMode=self.settings.s3_retention_mode,
                ObjectLockRetainUntilDate=datetime.now(UTC)
                + timedelta(days=self.settings.s3_retention_days),
            )
        return self.client.put_object(
            Bucket=self.settings.s3_bucket,
            Key=self.key(firm_id, path),
            Body=content,
            **checksum,
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
