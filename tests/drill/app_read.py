"""Prove the application can read a (restored) database: ORM reads, audit chain verify, file checksums."""
import hashlib
import os
import sys

import boto3
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.audit import verify
from app.database.models import AuditLog, Document, Firm

engine = create_engine(os.environ["TARGET_DB_URL"])
s3 = boto3.client("s3", endpoint_url=os.environ["BACKUP_S3_ENDPOINT"], aws_access_key_id="drill",
                  aws_secret_access_key="drill-secret", region_name="us-east-1")
with Session(engine) as db:
    firms = db.scalars(select(Firm)).all()
    docs = db.scalars(select(Document)).all()
    rows = db.scalars(select(AuditLog).where(AuditLog.firm_id == firms[0].id).order_by(AuditLog.sequence)).all()
    chain = verify(rows)
    bad = 0
    for d in docs:
        key = d.egnyte_path.split("/", 3)[3]
        got = hashlib.sha256(s3.get_object(Bucket=os.environ["BACKUP_BUCKET"], Key=key)["Body"].read()).hexdigest()
        bad += got != d.sha256
print(f"firms={len(firms)} documents={len(docs)} audit_chain={chain} checksum_mismatches={bad}")
sys.exit(0 if chain["valid"] and chain["checked"] == 15 and docs and bad == 0 else 1)
