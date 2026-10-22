"""SQLAlchemy models.

Tenant-owned records carry ``firm_id`` even when it could be reached through another
relationship. That makes tenant filters explicit and reviewable at every query boundary.
"""

from __future__ import annotations

import enum
import uuid
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.checklist import ClientStatus


def new_id() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class UserRole(enum.StrEnum):
    CLIENT = "client"
    AUDITOR = "auditor"


class EngagementStatus(enum.StrEnum):
    DRAFT = "draft"
    COLLECTING = "collecting"
    TESTING = "testing"
    AUDITOR_REVIEW = "auditor_review"
    COMPLETE = "complete"


class ReviewState(enum.StrEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    EDITED = "edited"
    REJECTED = "rejected"


class NAReviewState(enum.StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class Firm(Base):
    __tablename__ = "firms"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(255))
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    users: Mapped[list[User]] = relationship(back_populates="firm")
    engagements: Mapped[list[Engagement]] = relationship(back_populates="firm")


class User(Base):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("firm_id", "email", name="uq_users_firm_email"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    firm_id: Mapped[str | None] = mapped_column(ForeignKey("firms.id"), index=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(Enum(UserRole, native_enum=False), index=True)
    password_hash: Mapped[str | None] = mapped_column(String(255))
    mfa_secret: Mapped[str | None] = mapped_column(String(64))
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    invited_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    firm: Mapped[Firm | None] = relationship(back_populates="users")
    assigned_engagements: Mapped[list[Engagement]] = relationship(
        back_populates="auditor", foreign_keys="Engagement.auditor_id"
    )


class Engagement(Base):
    __tablename__ = "engagements"
    __table_args__ = (
        CheckConstraint("review_period_end >= review_period_start", name="ck_engagement_period"),
        Index("ix_engagements_firm_status", "firm_id", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    firm_id: Mapped[str] = mapped_column(ForeignKey("firms.id"), index=True)
    auditor_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), index=True)
    engagement_type: Mapped[str] = mapped_column(
        String(255), default="FINRA Rule 3310 Independent AML Test"
    )
    status: Mapped[EngagementStatus] = mapped_column(
        Enum(EngagementStatus, native_enum=False), default=EngagementStatus.COLLECTING
    )
    review_period_start: Mapped[date] = mapped_column(Date)
    review_period_end: Mapped[date] = mapped_column(Date)
    due_date: Mapped[date | None] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    firm: Mapped[Firm] = relationship(back_populates="engagements")
    auditor: Mapped[User | None] = relationship(
        back_populates="assigned_engagements", foreign_keys=[auditor_id]
    )
    items: Mapped[list[ChecklistItemInstance]] = relationship(
        back_populates="engagement",
        cascade="all, delete-orphan",
        order_by="ChecklistItemInstance.position",
    )


class ChecklistItemInstance(Base):
    __tablename__ = "checklist_item_instances"
    __table_args__ = (
        UniqueConstraint("engagement_id", "item_key", name="uq_engagement_item_key"),
        Index("ix_checklist_items_firm_engagement", "firm_id", "engagement_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    firm_id: Mapped[str] = mapped_column(ForeignKey("firms.id"), index=True)
    engagement_id: Mapped[str] = mapped_column(ForeignKey("engagements.id"), index=True)
    item_key: Mapped[str] = mapped_column(String(120))
    section_key: Mapped[str] = mapped_column(String(120))
    section_title: Mapped[str] = mapped_column(String(255))
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text, default="")
    position: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[ClientStatus] = mapped_column(
        Enum(ClientStatus, native_enum=False), default=ClientStatus.REQUESTED
    )
    client_reason: Mapped[str | None] = mapped_column(Text)
    restricted: Mapped[bool] = mapped_column(Boolean, default=False)
    is_conditional: Mapped[bool] = mapped_column(Boolean, default=False)
    condition_question: Mapped[str | None] = mapped_column(Text)
    applicable: Mapped[bool] = mapped_column(Boolean, default=True)
    applicability_answer: Mapped[bool | None] = mapped_column(Boolean)
    na_review_state: Mapped[NAReviewState | None] = mapped_column(
        Enum(NAReviewState, native_enum=False)
    )
    na_requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    na_approved_by_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    engagement: Mapped[Engagement] = relationship(back_populates="items")
    documents: Mapped[list[Document]] = relationship(
        back_populates="item", cascade="all, delete-orphan", order_by="Document.created_at"
    )


class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (
        UniqueConstraint("item_instance_id", "egnyte_path", "version", name="uq_document_version"),
        Index("ix_documents_firm_item", "firm_id", "item_instance_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    firm_id: Mapped[str] = mapped_column(ForeignKey("firms.id"), index=True)
    item_instance_id: Mapped[str] = mapped_column(
        ForeignKey("checklist_item_instances.id"), index=True
    )
    uploaded_by_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    original_name: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str | None] = mapped_column(String(255))
    size_bytes: Mapped[int] = mapped_column(Integer)
    egnyte_path: Mapped[str] = mapped_column(String(1024))
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    version: Mapped[str] = mapped_column(String(255), default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    item: Mapped[ChecklistItemInstance] = relationship(back_populates="documents")
    check_results: Mapped[list[CheckResult]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )


class CheckResult(Base):
    __tablename__ = "check_results"
    __table_args__ = (Index("ix_check_results_firm_document", "firm_id", "document_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    firm_id: Mapped[str] = mapped_column(ForeignKey("firms.id"), index=True)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"), index=True)
    check_type: Mapped[str] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(50))
    client_reason: Mapped[str | None] = mapped_column(Text)
    details: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    citations: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    document: Mapped[Document] = relationship(back_populates="check_results")


class FindingDraft(Base):
    __tablename__ = "finding_drafts"
    __table_args__ = (Index("ix_findings_firm_engagement", "firm_id", "engagement_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    firm_id: Mapped[str] = mapped_column(ForeignKey("firms.id"), index=True)
    engagement_id: Mapped[str] = mapped_column(ForeignKey("engagements.id"), index=True)
    document_id: Mapped[str | None] = mapped_column(ForeignKey("documents.id"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    body: Mapped[str] = mapped_column(Text)
    severity: Mapped[str] = mapped_column(String(50))
    citations: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    review_state: Mapped[ReviewState] = mapped_column(
        Enum(ReviewState, native_enum=False), default=ReviewState.PENDING
    )
    reviewed_by_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (Index("ix_audit_logs_firm_created", "firm_id", "created_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    firm_id: Mapped[str | None] = mapped_column(ForeignKey("firms.id"), index=True)
    actor_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), index=True)
    action: Mapped[str] = mapped_column(String(120))
    entity_type: Mapped[str] = mapped_column(String(120))
    entity_id: Mapped[str | None] = mapped_column(String(36))
    details: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AuthSession(Base):
    __tablename__ = "auth_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class MagicLinkToken(Base):
    __tablename__ = "magic_link_tokens"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
