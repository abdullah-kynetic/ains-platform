"""Tenant-scoped engagement and document endpoints used by the client portal."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Annotated, Protocol

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel
from sqlalchemy import Select, select
from sqlalchemy.orm import Session, selectinload

from app.auth.dependencies import get_current_user
from app.checklist import ClientStatus
from app.database.models import (
    AuditLog,
    ChecklistItemInstance,
    Document,
    Engagement,
    EngagementStatus,
    User,
    UserRole,
)
from app.database.session import get_db

router = APIRouter(tags=["engagements"])
DB = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


class APIModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)


class FileView(APIModel):
    id: str
    name: str
    size: int
    uploaded_at: datetime


class ItemView(APIModel):
    id: str
    title: str
    description: str
    status: ClientStatus
    reason: str | None
    restricted: bool
    files: list[FileView]


class SectionView(APIModel):
    id: str
    title: str
    items: list[ItemView]


class ReviewPeriodView(APIModel):
    start: str
    end: str


class EngagementView(APIModel):
    id: str
    firm_name: str
    engagement_type: str
    review_period: ReviewPeriodView
    due_date: str | None
    sections: list[SectionView]


class DocumentView(APIModel):
    id: str
    name: str
    size: int
    sha256: str
    version: str
    status: ClientStatus


@dataclass(frozen=True)
class StoredDocument:
    egnyte_path: str
    sha256: str
    size_bytes: int
    version: str = "1"


class DocumentIngestor(Protocol):
    async def ingest(
        self, *, engagement: Engagement, item: ChecklistItemInstance, file: UploadFile
    ) -> StoredDocument: ...


class UnconfiguredDocumentIngestor:
    async def ingest(
        self, *, engagement: Engagement, item: ChecklistItemInstance, file: UploadFile
    ) -> StoredDocument:
        del engagement, item, file
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Document storage is not configured",
        )


def get_document_ingestor() -> DocumentIngestor:
    return UnconfiguredDocumentIngestor()


Ingestor = Annotated[DocumentIngestor, Depends(get_document_ingestor)]
UploadedFile = Annotated[UploadFile, File()]


def visible_engagements(user: User) -> Select[tuple[Engagement]]:
    stmt = select(Engagement)
    if user.role == UserRole.AUDITOR:
        return stmt.where(Engagement.auditor_id == user.id)
    if not user.firm_id:
        return stmt.where(Engagement.id.is_(None))
    return stmt.where(Engagement.firm_id == user.firm_id)


def _serialize_engagement(engagement: Engagement) -> EngagementView:
    sections: dict[str, SectionView] = {}
    for item in engagement.items:
        if not item.applicable:
            continue
        section = sections.setdefault(
            item.section_key,
            SectionView(id=item.section_key, title=item.section_title, items=[]),
        )
        section.items.append(
            ItemView(
                id=item.id,
                title=item.title,
                description=item.description,
                status=item.status,
                reason=item.client_reason,
                restricted=item.restricted,
                files=[
                    FileView(
                        id=document.id,
                        name=document.original_name,
                        size=document.size_bytes,
                        uploaded_at=document.created_at,
                    )
                    for document in item.documents
                ],
            )
        )
    return EngagementView(
        id=engagement.id,
        firm_name=engagement.firm.name,
        engagement_type=engagement.engagement_type,
        review_period=ReviewPeriodView(
            start=engagement.review_period_start.isoformat(),
            end=engagement.review_period_end.isoformat(),
        ),
        due_date=engagement.due_date.isoformat() if engagement.due_date else None,
        sections=list(sections.values()),
    )


@router.get(
    "/engagements/current",
    response_model=EngagementView,
    response_model_by_alias=True,
)
def current_engagement(user: CurrentUser, db: DB) -> EngagementView:
    engagement = db.scalar(
        visible_engagements(user)
        .where(Engagement.status != EngagementStatus.COMPLETE)
        .options(
            selectinload(Engagement.firm),
            selectinload(Engagement.items).selectinload(ChecklistItemInstance.documents),
        )
        .order_by(Engagement.created_at.desc())
        .limit(1)
    )
    if not engagement:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active engagement")
    return _serialize_engagement(engagement)


@router.post(
    "/engagements/{engagement_id}/items/{item_id}/documents",
    response_model=DocumentView,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    engagement_id: str,
    item_id: str,
    file: UploadedFile,
    user: CurrentUser,
    db: DB,
    ingestor: Ingestor,
) -> DocumentView:
    engagement = db.scalar(visible_engagements(user).where(Engagement.id == engagement_id))
    if not engagement:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Engagement not found")
    item = db.scalar(
        select(ChecklistItemInstance).where(
            ChecklistItemInstance.id == item_id,
            ChecklistItemInstance.engagement_id == engagement.id,
            ChecklistItemInstance.firm_id == engagement.firm_id,
        )
    )
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Checklist item not found"
        )
    if item.restricted:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This restricted item must be handled directly with the auditor",
        )

    stored = await ingestor.ingest(engagement=engagement, item=item, file=file)
    document = Document(
        firm_id=engagement.firm_id,
        item_instance_id=item.id,
        uploaded_by_id=user.id,
        original_name=file.filename or "upload",
        content_type=file.content_type,
        size_bytes=stored.size_bytes,
        egnyte_path=stored.egnyte_path,
        sha256=stored.sha256,
        version=stored.version,
    )
    item.status = ClientStatus.CHECKING
    item.client_reason = None
    db.add(document)
    db.flush()
    db.add(
        AuditLog(
            firm_id=engagement.firm_id,
            actor_id=user.id,
            action="document.created",
            entity_type="checklist_item_instance",
            entity_id=item.id,
            details={"document_id": document.id},
        )
    )
    db.commit()
    db.refresh(document)
    return DocumentView(
        id=document.id,
        name=document.original_name,
        size=document.size_bytes,
        sha256=document.sha256,
        version=document.version,
        status=item.status,
    )
