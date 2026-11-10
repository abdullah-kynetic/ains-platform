"""Auditing practice routes: team, branding, rubric and request templates (L2-6a).

The practice is always the signed-in auditor's own (``User.practice_id``); no route accepts a
practice id, so another practice's data cannot be addressed. Member and template ids are
resolved inside that practice only. Clients never reach these routes. No criteria are invented:
rubric text stays empty until a partner writes it, and the only built-in template is the full
catalog. Practice-level changes are written to the audit chain with no client firm.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.alias_generators import to_camel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.checklist.catalog import load_catalog
from app.database.models import (
    AuditLog,
    AuthSession,
    Engagement,
    Practice,
    PracticeRubricItem,
    PracticeTemplate,
    User,
    UserRole,
)
from app.tenancy import require_logo_url

from .engagements import DB, CurrentUser

router = APIRouter(prefix="/auditor/firm", tags=["firm"])

TeamRole = Literal["partner", "reviewer", "auditor", "admin"]
TemplateKind = Literal["clearing", "introducing", "retail", "custom"]
ALL_TEMPLATE_ID = "tpl-all"


class Body(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="forbid")


class View(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class TeamMemberView(View):
    id: str
    name: str
    email: str
    role: TeamRole
    status: Literal["active", "invited"]


class InviteBody(Body):
    email: str = Field(min_length=3, max_length=320)
    role: TeamRole

    @field_validator("email")
    @classmethod
    def valid_email(cls, value: str) -> str:
        normalized = value.strip().casefold()
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", normalized):
            raise ValueError("Enter a valid email address")
        return normalized


class RoleBody(Body):
    role: TeamRole


class BrandingBody(Body):
    name: str = Field(min_length=1, max_length=120)
    # The contract field keeps its web name; only a site path or https URL is accepted, never a
    # data URL (the file itself goes to object storage in L2-7).
    logo_data_url: str | None = Field(default=None, max_length=500)
    tagline: str = Field(default="", max_length=200)

    @field_validator("name", "tagline")
    @classmethod
    def trimmed(cls, value: str) -> str:
        return value.strip()

    @field_validator("name")
    @classmethod
    def named(cls, value: str) -> str:
        if not value:
            raise ValueError("A firm name is required")
        return value

    @field_validator("logo_data_url")
    @classmethod
    def public_logo(cls, value: str | None) -> str | None:
        return require_logo_url(value or None)


class BrandingView(View):
    name: str
    logo_data_url: str | None
    tagline: str


class RubricItemView(View):
    request_id: str
    title: str
    section: str
    criteria: str
    enabled: bool


class RubricBody(BaseModel):
    """The web sends the whole item; only criteria and enabled are writable."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="ignore")
    criteria: str = Field(default="", max_length=4000)
    enabled: bool = True


class TemplateView(View):
    id: str
    name: str
    kind: TemplateKind
    description: str
    request_ids: list[str]


class TemplateBody(Body):
    name: str = Field(min_length=1, max_length=120)
    kind: TemplateKind
    description: str = Field(default="", max_length=500)
    request_ids: list[str] = Field(min_length=1, max_length=64)

    @field_validator("name")
    @classmethod
    def named(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("A template name is required")
        return value

    @field_validator("request_ids")
    @classmethod
    def known_unique(cls, value: list[str]) -> list[str]:
        known = {request.id for request in load_catalog().requests}
        if len(set(value)) != len(value) or not set(value) <= known:
            raise ValueError("Request ids must be unique catalog ids")
        return value


# --- scope and authorization -------------------------------------------------------------


def _practice(db: Session, user: User) -> Practice:
    if user.role != UserRole.AUDITOR:
        raise HTTPException(403, "Auditor access required")
    practice = db.get(Practice, user.practice_id) if user.practice_id else None
    if practice is None:
        raise HTTPException(403, "No audit practice membership")
    return practice


def _role(user: User) -> str:
    return user.team_role or "auditor"


def _require(user: User, *roles: str) -> None:
    if _role(user) not in roles:
        raise HTTPException(403, "Your team role cannot do this")


def _log(db: Session, user: User, practice: Practice, action: str, entity: str, entity_id, **d):
    db.add(
        AuditLog(
            firm_id=None,
            actor_id=user.id,
            action=action,
            entity_type=entity,
            entity_id=entity_id,
            details={"practice_id": practice.id, **d},
        )
    )


# --- team --------------------------------------------------------------------------------


def _member_view(user: User) -> TeamMemberView:
    invited = not user.is_active and user.accepted_at is None
    return TeamMemberView(
        id=user.id,
        name=user.name,
        email=user.email,
        role=_role(user),  # type: ignore[arg-type]
        status="invited" if invited else "active",
    )


def _team(db: Session, practice: Practice) -> list[TeamMemberView]:
    users = db.scalars(
        select(User)
        .where(User.practice_id == practice.id, User.role == UserRole.AUDITOR)
        .order_by(User.name, User.email)
    ).all()
    return [_member_view(user) for user in users]


def _member(db: Session, practice: Practice, member_id: str) -> User:
    member = db.scalar(
        select(User).where(
            User.id == member_id,
            User.practice_id == practice.id,
            User.role == UserRole.AUDITOR,
        )
    )
    if member is None:
        raise HTTPException(404, "Team member not found")
    return member


def _partner_count(db: Session, practice: Practice) -> int:
    return (
        db.scalar(
            select(func.count())
            .select_from(User)
            .where(
                User.practice_id == practice.id,
                User.team_role == "partner",
                User.is_active.is_(True),
            )
        )
        or 0
    )


def _may_touch(actor: User, target_role: str, new_role: str | None = None) -> None:
    """Only a partner can grant, change or remove the partner role."""
    _require(actor, "partner", "admin")
    if "partner" in {target_role, new_role} and _role(actor) != "partner":
        raise HTTPException(403, "Only a partner can change a partner")


@router.get("/team", response_model=list[TeamMemberView], response_model_by_alias=True)
def list_team(db: DB, user: CurrentUser) -> list[TeamMemberView]:
    return _team(db, _practice(db, user))


@router.post(
    "/team", response_model=list[TeamMemberView], status_code=201, response_model_by_alias=True
)
def invite_member(body: InviteBody, db: DB, user: CurrentUser) -> list[TeamMemberView]:
    practice = _practice(db, user)
    _may_touch(user, "auditor", body.role)
    if db.scalar(select(User.id).where(func.lower(User.email) == body.email)):
        raise HTTPException(409, "That email already has an account")
    # Held inactive until the team sign-in flow exists; no email is sent from here.
    member = User(
        email=body.email,
        name=body.email.split("@")[0],
        role=UserRole.AUDITOR,
        practice_id=practice.id,
        team_role=body.role,
        is_active=False,
    )
    db.add(member)
    db.flush()
    _log(db, user, practice, "team.invited", "user", member.id, role=body.role)
    db.commit()
    return _team(db, practice)


@router.patch(
    "/team/{member_id}", response_model=list[TeamMemberView], response_model_by_alias=True
)
def change_role(member_id: str, body: RoleBody, db: DB, user: CurrentUser) -> list[TeamMemberView]:
    practice = _practice(db, user)
    member = _member(db, practice, member_id)
    previous = _role(member)
    _may_touch(user, previous, body.role)
    if previous == "partner" and body.role != "partner" and _partner_count(db, practice) <= 1:
        raise HTTPException(409, "A firm needs at least one partner.")
    member.team_role = body.role
    _log(
        db,
        user,
        practice,
        "team.role_changed",
        "user",
        member.id,
        **{"from": previous, "to": body.role},
    )
    db.commit()
    return _team(db, practice)


@router.delete(
    "/team/{member_id}", response_model=list[TeamMemberView], response_model_by_alias=True
)
def remove_member(member_id: str, db: DB, user: CurrentUser) -> list[TeamMemberView]:
    practice = _practice(db, user)
    member = _member(db, practice, member_id)
    _may_touch(user, _role(member))
    if member.id == user.id:
        raise HTTPException(409, "You cannot remove yourself.")
    if _role(member) == "partner" and _partner_count(db, practice) <= 1:
        raise HTTPException(409, "A firm needs at least one partner.")
    if db.scalar(
        select(func.count()).select_from(Engagement).where(Engagement.auditor_id == member.id)
    ):
        raise HTTPException(409, "Reassign this member's engagements first.")
    removed = member.id
    never_signed_in = member.accepted_at is None and not member.is_active
    _log(db, user, practice, "team.removed", "user", removed, role=_role(member))
    if never_signed_in:
        db.delete(member)
    else:
        member.is_active = False
        member.practice_id = None
        member.team_role = None
        for session in db.scalars(
            select(AuthSession).where(
                AuthSession.user_id == removed, AuthSession.revoked_at.is_(None)
            )
        ):
            session.revoked_at = datetime.now(UTC)
    db.commit()
    return _team(db, practice)


# --- branding ----------------------------------------------------------------------------


def _branding(practice: Practice) -> BrandingView:
    return BrandingView(
        name=practice.name, logo_data_url=practice.logo_url, tagline=practice.tagline
    )


@router.get("/branding", response_model=BrandingView, response_model_by_alias=True)
def get_branding(db: DB, user: CurrentUser) -> BrandingView:
    return _branding(_practice(db, user))


@router.put("/branding", response_model=BrandingView, response_model_by_alias=True)
def save_branding(body: BrandingBody, db: DB, user: CurrentUser) -> BrandingView:
    practice = _practice(db, user)
    _require(user, "partner", "admin")
    practice.name = body.name
    practice.tagline = body.tagline
    practice.logo_url = body.logo_data_url
    _log(db, user, practice, "branding.updated", "practice", practice.id)
    db.commit()
    return _branding(practice)


# --- rubric ------------------------------------------------------------------------------


def _rubric(db: Session, practice: Practice) -> list[RubricItemView]:
    overrides = {
        row.request_id: row
        for row in db.scalars(
            select(PracticeRubricItem).where(PracticeRubricItem.practice_id == practice.id)
        )
    }
    items = []
    for request in load_catalog().requests:
        row = overrides.get(request.id)
        items.append(
            RubricItemView(
                request_id=request.id,
                title=request.title,
                section=request.section,
                criteria=row.criteria if row else "",
                enabled=row.enabled if row else True,
            )
        )
    return items


@router.get("/rubric", response_model=list[RubricItemView], response_model_by_alias=True)
def get_rubric(db: DB, user: CurrentUser) -> list[RubricItemView]:
    return _rubric(db, _practice(db, user))


@router.put("/rubric/{request_id}", response_model=RubricItemView, response_model_by_alias=True)
def save_rubric_item(
    request_id: str, body: RubricBody, db: DB, user: CurrentUser
) -> RubricItemView:
    practice = _practice(db, user)
    _require(user, "partner")  # partner-approved criteria only
    if load_catalog().get(request_id) is None:
        raise HTTPException(404, "Request not found")
    row = db.scalar(
        select(PracticeRubricItem).where(
            PracticeRubricItem.practice_id == practice.id,
            PracticeRubricItem.request_id == request_id,
        )
    )
    if row is None:
        row = PracticeRubricItem(practice_id=practice.id, request_id=request_id)
        db.add(row)
    row.criteria = body.criteria.strip()
    row.enabled = body.enabled
    row.updated_by_id = user.id
    row.updated_at = datetime.now(UTC)
    _log(db, user, practice, "rubric.updated", "request", request_id, enabled=body.enabled)
    db.commit()
    return next(item for item in _rubric(db, practice) if item.request_id == request_id)


# --- request templates -------------------------------------------------------------------


def _templates(db: Session, practice: Practice) -> list[TemplateView]:
    all_ids = [request.id for request in load_catalog().requests]
    built_in = TemplateView(
        id=ALL_TEMPLATE_ID,
        name="Full Rule 3310 request list",
        kind="custom",
        description=f"All {len(all_ids)} requests, the default for a new engagement.",
        request_ids=all_ids,
    )
    rows = db.scalars(
        select(PracticeTemplate)
        .where(PracticeTemplate.practice_id == practice.id)
        .order_by(PracticeTemplate.created_at, PracticeTemplate.id)
    ).all()
    return [built_in] + [
        TemplateView(
            id=row.id,
            name=row.name,
            kind=row.kind,  # type: ignore[arg-type]
            description=row.description,
            request_ids=list(row.request_ids),
        )
        for row in rows
    ]


def _template(db: Session, practice: Practice, template_id: str) -> PracticeTemplate:
    if template_id == ALL_TEMPLATE_ID:
        raise HTTPException(409, "The built-in template cannot be changed.")
    row = db.scalar(
        select(PracticeTemplate).where(
            PracticeTemplate.id == template_id, PracticeTemplate.practice_id == practice.id
        )
    )
    if row is None:
        raise HTTPException(404, "Template not found")
    return row


@router.get("/request-templates", response_model=list[TemplateView], response_model_by_alias=True)
def list_templates(db: DB, user: CurrentUser) -> list[TemplateView]:
    return _templates(db, _practice(db, user))


@router.post(
    "/request-templates",
    response_model=list[TemplateView],
    status_code=201,
    response_model_by_alias=True,
)
def create_template(body: TemplateBody, db: DB, user: CurrentUser) -> list[TemplateView]:
    practice = _practice(db, user)
    _require(user, "partner", "admin")
    row = PracticeTemplate(
        practice_id=practice.id,
        name=body.name,
        kind=body.kind,
        description=body.description.strip(),
        request_ids=body.request_ids,
    )
    db.add(row)
    db.flush()
    _log(db, user, practice, "template.created", "template", row.id, requests=len(row.request_ids))
    db.commit()
    return _templates(db, practice)


@router.put(
    "/request-templates/{template_id}",
    response_model=list[TemplateView],
    response_model_by_alias=True,
)
def update_template(
    template_id: str, body: TemplateBody, db: DB, user: CurrentUser
) -> list[TemplateView]:
    practice = _practice(db, user)
    _require(user, "partner", "admin")
    row = _template(db, practice, template_id)
    row.name = body.name
    row.kind = body.kind
    row.description = body.description.strip()
    row.request_ids = body.request_ids
    _log(db, user, practice, "template.updated", "template", row.id, requests=len(row.request_ids))
    db.commit()
    return _templates(db, practice)


@router.delete(
    "/request-templates/{template_id}",
    response_model=list[TemplateView],
    response_model_by_alias=True,
)
def delete_template(template_id: str, db: DB, user: CurrentUser) -> list[TemplateView]:
    practice = _practice(db, user)
    _require(user, "partner", "admin")
    row = _template(db, practice, template_id)
    _log(db, user, practice, "template.deleted", "template", row.id)
    db.delete(row)
    db.commit()
    return _templates(db, practice)
