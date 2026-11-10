"""SQLAlchemy models.

Tenant-owned records carry ``firm_id`` even when it could be reached through another
relationship. That makes tenant filters explicit and reviewable at every query boundary.
"""

from __future__ import annotations

import enum
import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, validates

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
    REPORT_DRAFTING = "report_drafting"
    AWAITING_SIGNATURE = "awaiting_signature"
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


class CheckJobStatus(enum.StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class TaskPriority(enum.StrEnum):
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"


class Firm(Base):
    __tablename__ = "firms"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(255))
    # Portal label: https://{slug}.<portal base>. Unique, lowercase, not a reserved host.
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    # Public mark only. Relative path or https URL. Never other firm data.
    logo_url: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    users: Mapped[list[User]] = relationship(back_populates="firm")
    engagements: Mapped[list[Engagement]] = relationship(back_populates="firm")

    @validates("slug")
    def _validate_slug(self, _key: str, value: str) -> str:
        from app.tenancy import require_firm_slug

        return require_firm_slug(value)

    @validates("logo_url")
    def _validate_logo_url(self, _key: str, value: str | None) -> str | None:
        from app.tenancy import require_logo_url

        return require_logo_url(value)


class Practice(Base):
    """The auditing practice: the team, branding, rubric and templates auditors work under.

    Distinct from ``Firm``, which is a client broker-dealer. Every practice route derives the
    practice from the signed-in user, never from a request id.
    """

    __tablename__ = "practices"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(120))
    tagline: Mapped[str] = mapped_column(String(200), default="")
    logo_url: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    @validates("logo_url")
    def _validate_logo_url(self, _key: str, value: str | None) -> str | None:
        from app.tenancy import require_logo_url

        return require_logo_url(value)


class PracticeRubricItem(Base):
    """Partner-set override for one catalog request. No row means defaults (empty, enabled)."""

    __tablename__ = "practice_rubric_items"
    __table_args__ = (UniqueConstraint("practice_id", "request_id", name="uq_practice_rubric"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    practice_id: Mapped[str] = mapped_column(ForeignKey("practices.id"), index=True)
    request_id: Mapped[str] = mapped_column(String(20))
    criteria: Mapped[str] = mapped_column(Text, default="")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    updated_by_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class PracticeTemplate(Base):
    __tablename__ = "practice_templates"
    __table_args__ = (Index("ix_practice_templates_practice", "practice_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    practice_id: Mapped[str] = mapped_column(ForeignKey("practices.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    kind: Mapped[str] = mapped_column(String(12))
    description: Mapped[str] = mapped_column(String(500), default="")
    request_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


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
    mfa_enrollment_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    invited_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    onboarding_state: Mapped[str | None] = mapped_column(String(12))
    onboarding_finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Auditor team membership (the auditing practice, not a client firm). Clients leave both unset.
    practice_id: Mapped[str | None] = mapped_column(ForeignKey("practices.id"), index=True)
    team_role: Mapped[str | None] = mapped_column(String(12))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    firm: Mapped[Firm | None] = relationship(back_populates="users")
    assigned_engagements: Mapped[list[Engagement]] = relationship(
        back_populates="auditor", foreign_keys="Engagement.auditor_id"
    )


class MFARecoveryCode(Base):
    __tablename__ = "mfa_recovery_codes"
    __table_args__ = (
        Index("ix_mfa_recovery_codes_user_active", "user_id", "used_at", "revoked_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    code_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ClientInvitation(Base):
    __tablename__ = "client_invitations"
    __table_args__ = (
        UniqueConstraint("email", name="uq_client_invitations_email"),
        Index("ix_client_invitations_firm_engagement", "firm_id", "engagement_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    firm_id: Mapped[str] = mapped_column(ForeignKey("firms.id"), index=True)
    engagement_id: Mapped[str] = mapped_column(ForeignKey("engagements.id"), index=True)
    email: Mapped[str] = mapped_column(String(320), index=True)
    name: Mapped[str] = mapped_column(String(255))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    created_by_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    accepted_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), unique=True)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
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
    checklist_version: Mapped[str | None] = mapped_column(String(120))
    checklist_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    review_period_start: Mapped[date] = mapped_column(Date)
    review_period_end: Mapped[date] = mapped_column(Date)
    due_date: Mapped[date | None] = mapped_column(Date)
    # Recorded workflow events. Each is set once by an explicit human action and audit-logged.
    checklist_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    checklist_sent_by_id: Mapped[str | None] = mapped_column(String(36))
    client_submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    report_confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    report_confirmed_by_id: Mapped[str | None] = mapped_column(String(36))
    report_confirmed_sha256: Mapped[str | None] = mapped_column(String(64))
    # Last allocated document sequence; document numbers are never reused or renumbered.
    document_seq: Mapped[int] = mapped_column(Integer, default=0)
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


class AuditorTask(Base):
    __tablename__ = "auditor_tasks"
    __table_args__ = (
        Index("ix_auditor_tasks_firm_engagement", "firm_id", "engagement_id"),
        Index("ix_auditor_tasks_assignee_completed", "assignee_id", "completed_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    firm_id: Mapped[str] = mapped_column(ForeignKey("firms.id"), index=True)
    engagement_id: Mapped[str] = mapped_column(ForeignKey("engagements.id"), index=True)
    assignee_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    request_id: Mapped[str | None] = mapped_column(String(120))
    due_date: Mapped[date | None] = mapped_column(Date)
    priority: Mapped[TaskPriority] = mapped_column(
        Enum(TaskPriority, native_enum=False), default=TaskPriority.NORMAL
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_by_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    engagement: Mapped[Engagement] = relationship()
    assignee: Mapped[User] = relationship(foreign_keys=[assignee_id])


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
    accepted_extensions: Mapped[list[str]] = mapped_column(JSON, default=list)
    review_period_rule: Mapped[str | None] = mapped_column(String(255))
    min_pages: Mapped[int] = mapped_column(Integer, default=1)
    requires_signature: Mapped[bool] = mapped_column(Boolean, default=False)
    position: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[ClientStatus] = mapped_column(
        Enum(ClientStatus, native_enum=False), default=ClientStatus.REQUESTED
    )
    na_previous_state: Mapped[dict[str, Any] | None] = mapped_column(JSON)
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
    # Client's required reason for a reasoned N/A request, and the auditor's decision note.
    na_request_reason: Mapped[str | None] = mapped_column(Text)
    na_decision_note: Mapped[str | None] = mapped_column(Text)
    na_decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Auditor's own test result for this request (pass, partial, fail or na); never inferred.
    conclusion: Mapped[str | None] = mapped_column(String(8))
    conclusion_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    conclusion_updated_by_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    # Client submitted this item for auditor review.
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    submitted_by_id: Mapped[str | None] = mapped_column(String(36))
    na_approved_by_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    # Legacy column also records the actor for direct client N/A declarations.
    na_marked_by: Mapped[User | None] = relationship(foreign_keys=[na_approved_by_id])
    representation: Mapped[str | None] = mapped_column(String(50))
    follow_up: Mapped[bool] = mapped_column(Boolean, default=False)
    # Explicit auditor release of a "Response requested" item. Only this text is client-visible.
    response_request_text: Mapped[str | None] = mapped_column(Text)
    response_released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    response_released_by_id: Mapped[str | None] = mapped_column(String(36))
    applicability_decision: Mapped[str | None] = mapped_column(String(30))
    assessment: Mapped[str | None] = mapped_column(String(30))
    internal_notes: Mapped[str] = mapped_column(Text, default="")
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
        UniqueConstraint("engagement_id", "number", name="uq_document_engagement_number"),
        Index("ix_documents_firm_item", "firm_id", "item_instance_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    firm_id: Mapped[str] = mapped_column(ForeignKey("firms.id"), index=True)
    engagement_id: Mapped[str | None] = mapped_column(ForeignKey("engagements.id"), index=True)
    item_instance_id: Mapped[str | None] = mapped_column(
        ForeignKey("checklist_item_instances.id"), index=True
    )
    uploaded_by_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    original_name: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str | None] = mapped_column(String(255))
    size_bytes: Mapped[int] = mapped_column(Integer)
    egnyte_path: Mapped[str] = mapped_column(String(1024))
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    version: Mapped[str] = mapped_column(String(255), default="1")
    feedback_code: Mapped[str | None] = mapped_column(String(50))
    # Stable citation such as "1.17"; assigned once per engagement at upload.
    number: Mapped[str | None] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    item: Mapped[ChecklistItemInstance | None] = relationship(back_populates="documents")
    check_results: Mapped[list[CheckResult]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )
    check_job: Mapped[CheckJob | None] = relationship(
        back_populates="document", cascade="all, delete-orphan", uselist=False
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


class CheckJob(Base):
    __tablename__ = "check_jobs"
    __table_args__ = (Index("ix_check_jobs_status_available", "status", "available_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    firm_id: Mapped[str] = mapped_column(ForeignKey("firms.id"), index=True)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"), unique=True, index=True)
    status: Mapped[CheckJobStatus] = mapped_column(
        Enum(CheckJobStatus, native_enum=False), default=CheckJobStatus.QUEUED
    )
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    last_error_code: Mapped[str | None] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    document: Mapped[Document] = relationship(back_populates="check_job")


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_firm_created", "firm_id", "created_at"),
        UniqueConstraint("firm_id", "sequence", name="uq_audit_firm_sequence"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    firm_id: Mapped[str | None] = mapped_column(ForeignKey("firms.id"), index=True)
    actor_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), index=True)
    action: Mapped[str] = mapped_column(String(120))
    entity_type: Mapped[str] = mapped_column(String(120))
    entity_id: Mapped[str | None] = mapped_column(String(36))
    ip_address: Mapped[str | None] = mapped_column(String(45))
    sequence: Mapped[int] = mapped_column(Integer)
    previous_hash: Mapped[str] = mapped_column(String(64))
    row_hash: Mapped[str] = mapped_column(String(64))
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


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AuthRateLimit(Base):
    __tablename__ = "auth_rate_limits"
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    count: Mapped[int] = mapped_column(Integer, default=0)
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class InvoiceIssuer(Base):
    """One numbering scope per auditor firm, or per legacy unbound auditor."""

    __tablename__ = "invoice_issuers"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    firm_id: Mapped[str | None] = mapped_column(ForeignKey("firms.id"), unique=True)
    auditor_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), unique=True)
    next_number: Mapped[int] = mapped_column(Integer, default=1)
    __table_args__ = (
        CheckConstraint(
            "(firm_id IS NULL) <> (auditor_id IS NULL)", name="ck_invoice_issuer_owner"
        ),
    )


class Invoice(Base):
    __tablename__ = "invoices"
    __table_args__ = (
        UniqueConstraint("issuer_id", "number", name="uq_invoice_issuer_number"),
        Index("ix_invoice_scope_status_due", "issuer_id", "status", "due_date"),
        Index("ix_invoice_client_issue", "firm_id", "issue_date"),
        CheckConstraint("status IN ('draft', 'sent', 'paid', 'void')", name="ck_invoice_status"),
        CheckConstraint("due_date >= issue_date", name="ck_invoice_dates"),
        CheckConstraint(
            "total_cents > 0 AND subtotal_cents = total_cents AND "
            "amount_paid_cents >= 0 AND amount_paid_cents <= total_cents",
            name="ck_invoice_amounts",
        ),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    issuer_id: Mapped[str] = mapped_column(ForeignKey("invoice_issuers.id"))
    firm_id: Mapped[str] = mapped_column(ForeignKey("firms.id"))
    engagement_id: Mapped[str | None] = mapped_column(ForeignKey("engagements.id"), index=True)
    auditor_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    number: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(12), default="draft")
    issue_date: Mapped[date] = mapped_column(Date)
    due_date: Mapped[date] = mapped_column(Date)
    notes: Mapped[str] = mapped_column(Text, default="")
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    subtotal_cents: Mapped[int] = mapped_column(BigInteger)
    total_cents: Mapped[int] = mapped_column(BigInteger)
    amount_paid_cents: Mapped[int] = mapped_column(BigInteger, default=0)
    paid_at: Mapped[date | None] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )
    firm: Mapped[Firm] = relationship()
    line_items: Mapped[list[InvoiceLineItem]] = relationship(
        cascade="all, delete-orphan", order_by="InvoiceLineItem.position"
    )
    events: Mapped[list[InvoiceEvent]] = relationship(order_by="InvoiceEvent.occurred_at")


class InvoiceLineItem(Base):
    __tablename__ = "invoice_line_items"
    __table_args__ = (
        UniqueConstraint("invoice_id", "position", name="uq_invoice_line_position"),
        CheckConstraint(
            "quantity > 0 AND rate_cents >= 0 AND amount_cents >= 0", name="ck_invoice_line_amounts"
        ),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    invoice_id: Mapped[str] = mapped_column(ForeignKey("invoices.id"), index=True)
    description: Mapped[str] = mapped_column(String(1000))
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    rate_cents: Mapped[int] = mapped_column(BigInteger)
    amount_cents: Mapped[int] = mapped_column(BigInteger)
    position: Mapped[int] = mapped_column(Integer)


class InvoiceEvent(Base):
    __tablename__ = "invoice_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    invoice_id: Mapped[str] = mapped_column(ForeignKey("invoices.id"), index=True)
    type: Mapped[str] = mapped_column(String(32))
    from_status: Mapped[str | None] = mapped_column(String(12))
    to_status: Mapped[str] = mapped_column(String(12))
    amount_cents: Mapped[int | None] = mapped_column(BigInteger)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    actor_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    details: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict)


class EngagementReport(Base):
    """Versioned human-authored report; finalization freezes the content snapshot."""

    __tablename__ = "engagement_reports"
    __table_args__ = (
        UniqueConstraint("engagement_id", name="uq_report_engagement"),
        CheckConstraint("status IN ('draft', 'final')", name="ck_report_status"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    firm_id: Mapped[str] = mapped_column(ForeignKey("firms.id"), index=True)
    engagement_id: Mapped[str] = mapped_column(ForeignKey("engagements.id"), index=True)
    created_by_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String(12), default="draft")
    version: Mapped[int] = mapped_column(Integer, default=1)
    content: Mapped[dict[str, Any]] = mapped_column(JSON)
    snapshot: Mapped[dict[str, Any]] = mapped_column(JSON)
    finalized_by_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    finalized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    content_sha256: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class ClientProfileDetails(Base):
    """Optional business metadata; missing values remain empty until supplied by a human."""

    __tablename__ = "client_profile_details"

    firm_id: Mapped[str] = mapped_column(ForeignKey("firms.id"), primary_key=True)
    firm_type: Mapped[str] = mapped_column(String(120), default="")
    crd: Mapped[str] = mapped_column(String(40), default="")
    clearing: Mapped[str] = mapped_column(String(255), default="")
    state: Mapped[str] = mapped_column(String(120), default="")


class ClientContact(Base):
    __tablename__ = "client_contacts"
    __table_args__ = (Index("ix_client_contacts_firm_id", "firm_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    firm_id: Mapped[str] = mapped_column(ForeignKey("firms.id"))
    name: Mapped[str] = mapped_column(String(255))
    title: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(320))
    phone: Mapped[str] = mapped_column(String(80))
    primary: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class DocumentItemLink(Base):
    """A client-made link from an uploaded document to a checklist item."""

    __tablename__ = "document_item_links"
    __table_args__ = (
        UniqueConstraint("item_instance_id", "document_id", name="uq_document_item_link"),
        Index("ix_document_item_links_firm_engagement", "firm_id", "engagement_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    firm_id: Mapped[str] = mapped_column(ForeignKey("firms.id"), index=True)
    engagement_id: Mapped[str] = mapped_column(ForeignKey("engagements.id"), index=True)
    item_instance_id: Mapped[str] = mapped_column(
        ForeignKey("checklist_item_instances.id"), index=True
    )
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"), index=True)
    linked_by_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class DocumentIssue(Base):
    """An auditor flag on a document (or a missing document) and its request thread."""

    __tablename__ = "document_issues"
    __table_args__ = (
        CheckConstraint(
            "kind IN ('outdated', 'wrong_year', 'incorrect', 'missing')", name="ck_issue_kind"
        ),
        CheckConstraint("status IN ('open', 'resolved')", name="ck_issue_status"),
        Index("ix_document_issues_firm_engagement", "firm_id", "engagement_id"),
        Index("ix_document_issues_item_status", "item_instance_id", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    firm_id: Mapped[str] = mapped_column(ForeignKey("firms.id"), index=True)
    engagement_id: Mapped[str] = mapped_column(ForeignKey("engagements.id"), index=True)
    item_instance_id: Mapped[str] = mapped_column(
        ForeignKey("checklist_item_instances.id"), index=True
    )
    document_id: Mapped[str | None] = mapped_column(ForeignKey("documents.id"), index=True)
    kind: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(12), default="open")
    created_by_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    resolved_by_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    messages: Mapped[list[IssueMessage]] = relationship(
        cascade="all, delete-orphan", order_by="IssueMessage.created_at"
    )


class IssueMessage(Base):
    __tablename__ = "issue_messages"
    __table_args__ = (Index("ix_issue_messages_firm_issue", "firm_id", "issue_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    firm_id: Mapped[str] = mapped_column(ForeignKey("firms.id"), index=True)
    issue_id: Mapped[str] = mapped_column(ForeignKey("document_issues.id"), index=True)
    author_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    author_role: Mapped[str] = mapped_column(String(12))
    body: Mapped[str] = mapped_column(Text)
    # Re-upload offered with this reply; must belong to the same engagement.
    document_id: Mapped[str | None] = mapped_column(ForeignKey("documents.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Workpaper(Base):
    """One workpaper per engagement request: the auditor's procedure, evidence and conclusion."""

    __tablename__ = "workpapers"
    __table_args__ = (
        UniqueConstraint("engagement_id", "request_id", name="uq_workpaper_engagement_request"),
        Index("ix_workpapers_firm_engagement", "firm_id", "engagement_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    firm_id: Mapped[str] = mapped_column(ForeignKey("firms.id"), index=True)
    engagement_id: Mapped[str] = mapped_column(ForeignKey("engagements.id"), index=True)
    request_id: Mapped[str] = mapped_column(String(20))
    procedure: Mapped[str] = mapped_column(Text, default="")
    # Documents in the same engagement that support the procedure.
    evidence_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    conclusion: Mapped[str | None] = mapped_column(String(8))
    preparer_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    prepared_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    reviewer_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class SampleSet(Base):
    __tablename__ = "sample_sets"
    __table_args__ = (Index("ix_sample_sets_firm_engagement", "firm_id", "engagement_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    firm_id: Mapped[str] = mapped_column(ForeignKey("firms.id"), index=True)
    engagement_id: Mapped[str] = mapped_column(ForeignKey("engagements.id"), index=True)
    area: Mapped[str] = mapped_column(String(200))
    request_id: Mapped[str | None] = mapped_column(String(20))
    population: Mapped[int] = mapped_column(Integer)
    sample_size: Mapped[int] = mapped_column(Integer)
    method: Mapped[str] = mapped_column(String(200))
    created_by_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    items: Mapped[list[SampleItem]] = relationship(
        cascade="all, delete-orphan", order_by="SampleItem.position"
    )


class SampleItem(Base):
    __tablename__ = "sample_items"
    __table_args__ = (
        CheckConstraint("result in ('pending','pass','exception')", name="ck_sample_item_result"),
        Index("ix_sample_items_firm_set", "firm_id", "set_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    firm_id: Mapped[str] = mapped_column(ForeignKey("firms.id"), index=True)
    set_id: Mapped[str] = mapped_column(ForeignKey("sample_sets.id"), index=True)
    position: Mapped[int] = mapped_column(Integer)
    reference: Mapped[str] = mapped_column(String(64))
    result: Mapped[str] = mapped_column(String(10), default="pending")
    note: Mapped[str] = mapped_column(Text, default="")
    updated_by_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Finding(Base):
    """An auditor-authored finding. Internal: no client route ever returns any of these fields.

    The client sees only a ``ResponseRequest`` the auditor explicitly writes and releases.
    Status: draft, approved (human approval with a citation), issued (a response was requested),
    responded (the client replied), closed. Distinct from ``FindingDraft`` (AI-era drafts).
    """

    __tablename__ = "findings"
    __table_args__ = (
        CheckConstraint(
            "status in ('draft','approved','issued','responded','closed')", name="ck_finding_status"
        ),
        CheckConstraint(
            "severity in ('low','moderate','high','critical')", name="ck_finding_severity"
        ),
        Index("ix_findings_records_firm_engagement", "firm_id", "engagement_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    firm_id: Mapped[str] = mapped_column(ForeignKey("firms.id"), index=True)
    engagement_id: Mapped[str] = mapped_column(ForeignKey("engagements.id"), index=True)
    title: Mapped[str] = mapped_column(String(255), default="")
    rule: Mapped[str] = mapped_column(Text, default="")
    condition: Mapped[str] = mapped_column(Text, default="")
    cause: Mapped[str] = mapped_column(Text, default="")
    effect: Mapped[str] = mapped_column(Text, default="")
    recommendation: Mapped[str] = mapped_column(Text, default="")
    severity: Mapped[str] = mapped_column(String(10), default="moderate")
    citations: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(10), default="draft")
    management_response: Mapped[str] = mapped_column(Text, default="")
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ResponseRequest(Base):
    """What a client sees of a finding: only text the auditor wrote when releasing it."""

    __tablename__ = "response_requests"
    __table_args__ = (
        UniqueConstraint("finding_id", name="uq_response_request_finding"),
        CheckConstraint("status in ('open','responded')", name="ck_response_request_status"),
        Index("ix_response_requests_firm_engagement", "firm_id", "engagement_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    firm_id: Mapped[str] = mapped_column(ForeignKey("firms.id"), index=True)
    engagement_id: Mapped[str] = mapped_column(ForeignKey("engagements.id"), index=True)
    finding_id: Mapped[str] = mapped_column(ForeignKey("findings.id"))
    title: Mapped[str] = mapped_column(String(255))
    request_text: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(10), default="open")
    response: Mapped[str] = mapped_column(Text, default="")
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    responded_by_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    released_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    released_by_id: Mapped[str] = mapped_column(ForeignKey("users.id"))


class ReportSectionEdit(Base):
    """An auditor's replacement text for one assembled report-draft section."""

    __tablename__ = "report_section_edits"
    __table_args__ = (
        UniqueConstraint("engagement_id", "section_id", name="uq_report_section_edit"),
        Index("ix_report_section_edits_firm_engagement", "firm_id", "engagement_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    firm_id: Mapped[str] = mapped_column(ForeignKey("firms.id"), index=True)
    engagement_id: Mapped[str] = mapped_column(ForeignKey("engagements.id"), index=True)
    section_id: Mapped[str] = mapped_column(String(80))
    body: Mapped[str] = mapped_column(Text)
    edited_by_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    edited_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
