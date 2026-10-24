"""Firm-bound client invitation issuance and acceptance."""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from typing import Annotated, Literal
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.alias_generators import to_camel
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.api.engagements import visible_engagements
from app.api.manual_review import require_auditor
from app.auth.dependencies import get_current_user
from app.auth.security import (
    hash_invitation_token,
    hash_password,
    new_invitation_token,
)
from app.config import Settings, get_settings
from app.database.models import (
    AuditLog,
    ClientInvitation,
    Engagement,
    Firm,
    User,
    UserRole,
)
from app.database.session import get_db

from .router import SessionView, _issue_session

public_router = APIRouter(prefix="/auth/invitations", tags=["client invitations"])
auditor_router = APIRouter(prefix="/auditor", tags=["client invitations"])

DB = Annotated[Session, Depends(get_db)]
AuthSettings = Annotated[Settings, Depends(get_settings)]
CurrentUser = Annotated[User, Depends(get_current_user)]
InvitationStatus = Literal["pending", "expired", "revoked", "accepted"]


class APIModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)


class InvitationCreate(APIModel):
    email: str = Field(min_length=3, max_length=320)
    name: str = Field(min_length=1, max_length=255)

    @field_validator("email")
    @classmethod
    def valid_email(cls, value: str) -> str:
        normalized = value.strip().casefold()
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", normalized):
            raise ValueError("Enter a valid email address")
        return normalized

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Client name is required")
        return cleaned


class InvitationView(APIModel):
    id: str
    firm_id: str
    engagement_id: str
    firm_name: str
    email: str
    name: str
    status: InvitationStatus
    expires_at: datetime
    accepted_at: datetime | None
    preview_path: str | None = None


class InvitationDetails(APIModel):
    firm_name: str
    email: str
    name: str
    expires_at: datetime


class InvitationAccept(APIModel):
    token: str = Field(min_length=20, max_length=512)
    password: str = Field(min_length=12, max_length=1024)


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=UTC)


def _invitation_status(
    invitation: ClientInvitation, now: datetime | None = None
) -> InvitationStatus:
    if invitation.accepted_at is not None:
        return "accepted"
    if invitation.revoked_at is not None:
        return "revoked"
    if _aware(invitation.expires_at) <= (now or datetime.now(UTC)):
        return "expired"
    return "pending"


def _assigned_engagement(db: Session, user: User, engagement_id: str) -> Engagement:
    require_auditor(user)
    engagement = db.scalar(
        visible_engagements(user)
        .where(Engagement.id == engagement_id)
        .options(selectinload(Engagement.firm))
    )
    if engagement is None:
        raise HTTPException(status_code=404, detail="Engagement not found")
    return engagement


def _assigned_invitation(db: Session, user: User, invitation_id: str) -> ClientInvitation:
    require_auditor(user)
    invitation = db.scalar(
        select(ClientInvitation)
        .join(Engagement, Engagement.id == ClientInvitation.engagement_id)
        .where(
            ClientInvitation.id == invitation_id,
            ClientInvitation.firm_id == Engagement.firm_id,
            Engagement.auditor_id == user.id,
        )
        .with_for_update()
    )
    if invitation is None:
        raise HTTPException(status_code=404, detail="Invitation not found")
    return invitation


def _view(
    db: Session,
    invitation: ClientInvitation,
    settings: Settings,
    *,
    token: str | None = None,
) -> InvitationView:
    firm = db.get(Firm, invitation.firm_id)
    preview_path = None
    if token is not None and settings.invitation_preview_enabled:
        preview_path = f"/accept-invitation?token={quote(token, safe='')}"
    return InvitationView(
        id=invitation.id,
        firm_id=invitation.firm_id,
        engagement_id=invitation.engagement_id,
        firm_name=firm.name if firm else "Client workspace",
        email=invitation.email,
        name=invitation.name,
        status=_invitation_status(invitation),
        expires_at=invitation.expires_at,
        accepted_at=invitation.accepted_at,
        preview_path=preview_path,
    )


@auditor_router.get("/engagements/{engagement_id}/invitations", response_model=list[InvitationView])
def list_invitations(
    engagement_id: str,
    user: CurrentUser,
    db: DB,
    settings: AuthSettings,
) -> list[InvitationView]:
    engagement = _assigned_engagement(db, user, engagement_id)
    invitations = db.scalars(
        select(ClientInvitation)
        .where(
            ClientInvitation.engagement_id == engagement.id,
            ClientInvitation.firm_id == engagement.firm_id,
        )
        .order_by(ClientInvitation.created_at.desc())
    ).all()
    return [_view(db, invitation, settings) for invitation in invitations]


@auditor_router.post(
    "/engagements/{engagement_id}/invitations",
    response_model=InvitationView,
    status_code=status.HTTP_201_CREATED,
)
def create_invitation(
    engagement_id: str,
    payload: InvitationCreate,
    user: CurrentUser,
    db: DB,
    settings: AuthSettings,
) -> InvitationView:
    engagement = _assigned_engagement(db, user, engagement_id)
    existing_user = db.scalar(select(User).where(User.email == payload.email))
    existing_invitation = db.scalar(
        select(ClientInvitation).where(ClientInvitation.email == payload.email)
    )
    if existing_user is not None:
        raise HTTPException(status_code=409, detail="This email already has an AINS account")
    if existing_invitation is not None:
        detail = (
            "This client is already invited to this firm; resend the existing invitation"
            if existing_invitation.firm_id == engagement.firm_id
            else "This email is already bound to another client firm"
        )
        raise HTTPException(status_code=409, detail=detail)

    now = datetime.now(UTC)
    token, token_hash = new_invitation_token()
    invitation = ClientInvitation(
        firm_id=engagement.firm_id,
        engagement_id=engagement.id,
        email=payload.email,
        name=payload.name,
        token_hash=token_hash,
        expires_at=now + timedelta(hours=settings.client_invitation_ttl_hours),
        created_by_id=user.id,
    )
    db.add(invitation)
    try:
        db.flush()
        db.add(
            AuditLog(
                firm_id=engagement.firm_id,
                actor_id=user.id,
                action="client_invitation.created",
                entity_type="client_invitation",
                entity_id=invitation.id,
                details={"email": invitation.email, "engagement_id": engagement.id},
            )
        )
        if not settings.invitation_preview_enabled:
            from .email import ResendSender

            ResendSender(settings, "invitation").send(
                email=invitation.email, token=token, expires_at=invitation.expires_at
            )
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="This email already has an invitation or account"
        ) from None
    return _view(db, invitation, settings, token=token)


@auditor_router.post("/invitations/{invitation_id}/resend", response_model=InvitationView)
def resend_invitation(
    invitation_id: str,
    user: CurrentUser,
    db: DB,
    settings: AuthSettings,
) -> InvitationView:
    invitation = _assigned_invitation(db, user, invitation_id)
    if invitation.accepted_at is not None:
        raise HTTPException(status_code=409, detail="Accepted invitations cannot be resent")
    if db.scalar(select(User.id).where(User.email == invitation.email)) is not None:
        raise HTTPException(status_code=409, detail="This email already has an AINS account")

    token, invitation.token_hash = new_invitation_token()
    invitation.expires_at = datetime.now(UTC) + timedelta(
        hours=settings.client_invitation_ttl_hours
    )
    invitation.revoked_at = None
    db.add(
        AuditLog(
            firm_id=invitation.firm_id,
            actor_id=user.id,
            action="client_invitation.resent",
            entity_type="client_invitation",
            entity_id=invitation.id,
            details={"email": invitation.email, "engagement_id": invitation.engagement_id},
        )
    )
    if not settings.invitation_preview_enabled:
        from .email import ResendSender

        ResendSender(settings, "invitation").send(
            email=invitation.email, token=token, expires_at=invitation.expires_at
        )
    db.commit()
    return _view(db, invitation, settings, token=token)


@auditor_router.post("/invitations/{invitation_id}/revoke", response_model=InvitationView)
def revoke_invitation(
    invitation_id: str,
    user: CurrentUser,
    db: DB,
    settings: AuthSettings,
) -> InvitationView:
    invitation = _assigned_invitation(db, user, invitation_id)
    if invitation.accepted_at is not None:
        raise HTTPException(status_code=409, detail="Accepted invitations cannot be revoked")
    if invitation.revoked_at is None:
        invitation.revoked_at = datetime.now(UTC)
        db.add(
            AuditLog(
                firm_id=invitation.firm_id,
                actor_id=user.id,
                action="client_invitation.revoked",
                entity_type="client_invitation",
                entity_id=invitation.id,
                details={"email": invitation.email, "engagement_id": invitation.engagement_id},
            )
        )
        db.commit()
    return _view(db, invitation, settings)


def _valid_invitation(db: Session, token: str, *, lock: bool = False) -> ClientInvitation:
    statement = select(ClientInvitation).where(
        ClientInvitation.token_hash == hash_invitation_token(token)
    )
    if lock:
        statement = statement.with_for_update()
    invitation = db.scalar(statement)
    if invitation is None:
        raise HTTPException(status_code=404, detail="Invitation is invalid")
    current_status = _invitation_status(invitation)
    if current_status == "accepted":
        raise HTTPException(status_code=410, detail="Invitation has already been used")
    if current_status == "revoked":
        raise HTTPException(status_code=410, detail="Invitation has been revoked")
    if current_status == "expired":
        raise HTTPException(status_code=410, detail="Invitation has expired")
    return invitation


@public_router.get("/{token}", response_model=InvitationDetails)
def invitation_details(token: str, db: DB) -> InvitationDetails:
    invitation = _valid_invitation(db, token)
    firm = db.get(Firm, invitation.firm_id)
    if firm is None:
        raise HTTPException(status_code=404, detail="Invitation is invalid")
    return InvitationDetails(
        firm_name=firm.name,
        email=invitation.email,
        name=invitation.name,
        expires_at=invitation.expires_at,
    )


@public_router.post("/accept", response_model=SessionView)
def accept_invitation(
    payload: InvitationAccept,
    response: Response,
    db: DB,
    settings: AuthSettings,
) -> SessionView:
    invitation = _valid_invitation(db, payload.token, lock=True)
    if db.scalar(select(User.id).where(User.email == invitation.email)) is not None:
        raise HTTPException(status_code=409, detail="This invitation can no longer be accepted")

    now = datetime.now(UTC)
    user = User(
        firm_id=invitation.firm_id,
        email=invitation.email,
        name=invitation.name,
        role=UserRole.CLIENT,
        password_hash=hash_password(payload.password),
        invited_at=invitation.created_at,
        accepted_at=now,
        is_active=True,
    )
    db.add(user)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="This invitation can no longer be accepted"
        ) from None
    invitation.accepted_at = now
    invitation.accepted_user_id = user.id
    db.add(
        AuditLog(
            firm_id=invitation.firm_id,
            actor_id=user.id,
            action="client_invitation.accepted",
            entity_type="client_invitation",
            entity_id=invitation.id,
            details={"email": invitation.email, "engagement_id": invitation.engagement_id},
        )
    )
    return _issue_session(db=db, settings=settings, response=response, user=user)
