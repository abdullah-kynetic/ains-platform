"""Seed SYNTHETIC data into the drill source database and S3 emulator. No real data, ever.

env: DATABASE_URL (via app.config), DRILL_S3_ENDPOINT. Prints no secrets.
"""

import hashlib
import os

import boto3
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.database.models import AuditLog, Base, Document, Firm, User, UserRole

BUCKET = "kien-prod-documents"


def main() -> None:
    engine = create_engine(os.environ["KIEN_DB_URL"])
    s3 = boto3.client(
        "s3",
        endpoint_url=os.environ["DRILL_S3_ENDPOINT"],
        aws_access_key_id="drill",
        aws_secret_access_key="drill-secret",
        region_name="us-east-1",
    )
    s3.create_bucket(Bucket=BUCKET)
    with Session(engine) as db:
        firm = Firm(name="Synthetic Firm", slug="synthetic-firm")
        db.add(firm)
        db.flush()
        auditor = User(
            firm_id=firm.id, email="a@synthetic.test", name="Syn Auditor", role=UserRole.AUDITOR
        )
        db.add(auditor)
        db.flush()
        for i in range(3):
            body = f"synthetic evidence file {i}\n".encode() * (50 + i)
            key = f"firms/{firm.id}/doc{i}.txt"
            s3.put_object(Bucket=BUCKET, Key=key, Body=body)
            db.add(
                Document(
                    firm_id=firm.id,
                    uploaded_by_id=auditor.id,
                    original_name=f"doc{i}.txt",
                    content_type="text/plain",
                    size_bytes=len(body),
                    egnyte_path=f"s3://{BUCKET}/{key}",
                    sha256=hashlib.sha256(body).hexdigest(),
                )
            )
        db.commit()
        for i in range(15):
            db.info["ip_address"] = "192.0.2.10"
            db.add(AuditLog(firm_id=firm.id, action="synthetic.view", entity_type="doc", entity_id=str(i)))
            db.commit()
    print("seeded")


if __name__ == "__main__":
    main()
