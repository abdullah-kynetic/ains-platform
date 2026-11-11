"""Assigned-auditor client profiles, contact records and engagement summaries."""

from collections.abc import Sequence
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models import (
    AuditLog,
    ClientContact,
    ClientProfileDetails,
    Engagement,
    EngagementStatus,
    Firm,
    User,
    UserRole,
)

from .engagements import DB, APIModel, CurrentUser

router = APIRouter(prefix="/auditor", tags=["client profiles"])


class ContactInput(APIModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=255, pattern=r"\S")
    title: str = Field(max_length=255)
    email: str = Field(min_length=3, max_length=320, pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
    phone: str = Field(max_length=80)


class ContactView(ContactInput):
    id: str
    primary: bool


class EngagementRef(APIModel):
    engagement_id: str
    period: str
    status: Literal["active", "complete"]
    signed_on: str | None


class ClientProfileView(APIModel):
    id: str
    firm_name: str
    firm_type: str
    crd: str
    clearing: str
    state: str
    onboarded_on: str
    contacts: list[ContactView]
    engagements: list[EngagementRef]


class EngagementSummaryView(APIModel):
    id: str
    client_id: str
    firm_name: str
    period: str
    stage: str
    due: str | None
    lead: str
    reviewer: str
    partner: str


def require_auditor(user: User) -> None:
    if user.role != UserRole.AUDITOR:
        raise HTTPException(403, "Auditor access required")


def assigned_for_firm(db: Session, user: User, firm_id: str) -> Sequence[Engagement]:
    # Client firm scope comes from an assignment, not the auditor's own issuing firm.
    return db.scalars(
        select(Engagement)
        .where(Engagement.firm_id == firm_id, Engagement.auditor_id == user.id)
        .order_by(Engagement.review_period_start.desc(), Engagement.id)
    ).all()


def engagement_summary(entry: Engagement) -> dict[str, str | None]:
    return {
        "id": entry.id,
        "clientId": entry.firm_id,
        "firmName": entry.firm.name,
        "period": (
            f"{entry.review_period_start.isoformat()} to {entry.review_period_end.isoformat()}"
        ),
        "stage": entry.status.value.replace("_", " ").title(),
        "due": entry.due_date.isoformat() if entry.due_date else None,
        "lead": entry.auditor.name if entry.auditor else "",
        # Reviewer/partner assignments belong to the later sign-off slice.
        "reviewer": "",
        "partner": "",
    }


def contact_view(contact: ClientContact) -> dict[str, object]:
    fields = ("id", "name", "title", "email", "phone", "primary")
    return {key: getattr(contact, key) for key in fields}


def profile_view(db: Session, firm: Firm, engagements: Sequence[Engagement]) -> dict[str, object]:
    details = db.scalar(select(ClientProfileDetails).where(ClientProfileDetails.firm_id == firm.id))
    contacts = db.scalars(
        select(ClientContact)
        .where(ClientContact.firm_id == firm.id)
        .order_by(ClientContact.created_at, ClientContact.id)
    ).all()
    return {
        "id": firm.id,
        "firmName": firm.name,
        "firmType": details.firm_type if details else "",
        "crd": details.crd if details else "",
        "clearing": details.clearing if details else "",
        "state": details.state if details else "",
        "onboardedOn": firm.created_at.date().isoformat(),
        "contacts": [contact_view(c) for c in contacts],
        "engagements": [
            {
                "engagementId": e.id,
                "period": engagement_summary(e)["period"],
                "status": "complete" if e.status == EngagementStatus.COMPLETE else "active",
                # A completed workflow is not proof that a report was signed.
                "signedOn": None,
            }
            for e in engagements
        ],
    }


@router.get("/clients", response_model=list[ClientProfileView])
def list_clients(user: CurrentUser, db: DB):
    require_auditor(user)
    firms = db.scalars(
        select(Firm)
        .where(Firm.id.in_(select(Engagement.firm_id).where(Engagement.auditor_id == user.id)))
        .order_by(Firm.name, Firm.id)
    ).all()
    return [profile_view(db, firm, assigned_for_firm(db, user, firm.id)) for firm in firms]


@router.get("/clients/{firm_id}", response_model=ClientProfileView)
def get_client(firm_id: str, user: CurrentUser, db: DB):
    require_auditor(user)
    engagements = assigned_for_firm(db, user, firm_id)
    if not engagements:
        raise HTTPException(404, "Client not found")
    firm = db.scalar(select(Firm).where(Firm.id == firm_id))
    return profile_view(db, firm, engagements)


@router.post("/clients/{firm_id}/contacts", status_code=201, response_model=ContactView)
def add_contact(firm_id: str, payload: ContactInput, user: CurrentUser, db: DB):
    require_auditor(user)
    if not assigned_for_firm(db, user, firm_id):
        raise HTTPException(404, "Client not found")
    contact = ClientContact(firm_id=firm_id, **payload.model_dump(), primary=False)
    db.add(contact)
    db.flush()
    db.add(
        AuditLog(
            firm_id=firm_id,
            actor_id=user.id,
            action="client.contact_created",
            entity_type="client_contact",
            entity_id=contact.id,
            details={"client_id": firm_id},
        )
    )
    db.commit()
    return contact_view(contact)


@router.get("/engagements/{engagement_id}/summary", response_model=EngagementSummaryView)
def get_summary(engagement_id: str, user: CurrentUser, db: DB):
    require_auditor(user)
    # Read-only. The assigned auditor, or a reviewer or partner of the assignee's practice, so a
    # second reviewer can open the file they are asked to approve.
    from .workpapers import _engagement_for_review

    entry = _engagement_for_review(db, user, engagement_id)
    return engagement_summary(entry)
