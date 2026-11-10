"""Authorized document downloads (S-19).

Every download is authorized on that request: a session, then the engagement scope (auditors:
assigned only; clients: own firm only), then the document's own firm and engagement. The reply
is a short-lived presigned link, never a public or stored URL. The bucket stays private.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.config import Settings, get_settings
from app.database.models import AuditLog, ChecklistItemInstance, Document, User, UserRole
from app.storage.s3 import S3Storage

from .engagements import DB, CurrentUser
from .questionnaire import _get_engagement

router = APIRouter(tags=["downloads"])
LINK_SECONDS = 60


def get_storage(settings: Annotated[Settings, Depends(get_settings)]) -> S3Storage | None:
    if settings.storage_backend != "s3" or not settings.s3_bucket:
        return None
    return S3Storage(settings)


Storage = Annotated["S3Storage | None", Depends(get_storage)]


def _download(
    db: DB, user: User, storage: S3Storage | None, engagement_id: str, document_id: str
) -> dict[str, object]:
    engagement = _get_engagement(db, user, engagement_id)
    document = db.get(Document, document_id)
    if (
        document is None
        or document.engagement_id != engagement.id
        or document.firm_id != engagement.firm_id
    ):
        raise HTTPException(404, "Document not found")
    if document.item_instance_id:
        item = db.get(ChecklistItemInstance, document.item_instance_id)
        if item is not None and (item.firm_id != engagement.firm_id or item.restricted):
            raise HTTPException(404, "Document not found")
    if storage is None:
        raise HTTPException(501, "Downloads need object storage")
    prefix = f"s3://{storage.settings.s3_bucket}/firms/{document.firm_id}/"
    receipt = document.egnyte_path
    if not receipt.startswith(prefix) or len(receipt) == len(prefix):
        raise HTTPException(404, "Document not found")
    url = storage.presign(document.firm_id, receipt[len(prefix) :], expires=LINK_SECONDS)
    db.add(
        AuditLog(
            firm_id=engagement.firm_id,
            actor_id=user.id,
            action="document.download_authorized",
            entity_type="document",
            entity_id=document.id,
            details={"role": user.role.value, "expires_in": LINK_SECONDS},
        )
    )
    db.commit()
    return {"url": url, "expiresIn": LINK_SECONDS, "name": document.original_name}


@router.get("/engagements/{engagement_id}/documents/{document_id}/download")
def client_download(
    engagement_id: str, document_id: str, user: CurrentUser, db: DB, storage: Storage
):
    if user.role != UserRole.CLIENT:
        raise HTTPException(403, "Only firm users can do this")
    return _download(db, user, storage, engagement_id, document_id)


@router.get("/auditor/engagements/{engagement_id}/documents/{document_id}/download")
def auditor_download(
    engagement_id: str, document_id: str, user: CurrentUser, db: DB, storage: Storage
):
    if user.role != UserRole.AUDITOR:
        raise HTTPException(403, "Auditor access required")
    return _download(db, user, storage, engagement_id, document_id)
