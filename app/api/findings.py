"""Findings and the response requests clients see (L2-6d).

Boundary: ``Finding`` rows (rule, condition, cause, effect, recommendation, severity, citations,
status) are auditor-only. A client route returns only a ``ResponseRequest``: the title and request
text an auditor wrote when explicitly releasing an approved finding, plus the client's own reply.
No client response carries a finding id, severity, citation or any finding field.

Only an auditor action approves a finding. Approval and release need every field and at least one
citation that names a document of this engagement and a page. Nothing here drafts or suggests text.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.alias_generators import to_camel
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.database.models import (
    AuditLog,
    Document,
    Engagement,
    Finding,
    ResponseRequest,
    User,
    UserRole,
)

from .engagements import DB, CurrentUser
from .questionnaire import _get_engagement

router = APIRouter(tags=["findings"])

Severity = Literal["low", "moderate", "high", "critical"]
Status = Literal["draft", "approved", "issued", "responded", "closed"]
# Moves an auditor may request directly. "issued" is reached only by releasing a response request,
# and "responded" only by the client's reply.
MOVES: dict[str, set[str]] = {
    "draft": {"approved"},
    "approved": {"draft"},
    "issued": {"closed"},
    "responded": {"closed"},
    "closed": set(),
}
TEXT_FIELDS = ("title", "rule", "condition", "cause", "effect", "recommendation")


class Body(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="forbid")


class View(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class Citation(Body):
    document: str = Field(min_length=1, max_length=255)
    page: int = Field(ge=1, le=100_000)


class FindingBody(Body):
    title: str = Field(default="", max_length=255)
    rule: str = Field(default="", max_length=8000)
    condition: str = Field(default="", max_length=8000)
    cause: str = Field(default="", max_length=8000)
    effect: str = Field(default="", max_length=8000)
    recommendation: str = Field(default="", max_length=8000)
    severity: Severity = "moderate"
    citations: list[Citation] = Field(default_factory=list, max_length=50)

    @field_validator(*TEXT_FIELDS)
    @classmethod
    def trimmed(cls, value: str) -> str:
        return value.strip()


class FindingView(View):
    id: str
    engagement_id: str
    title: str
    rule: str
    condition: str
    cause: str
    effect: str
    recommendation: str
    severity: Severity
    citations: list[Citation]
    management_response: str
    responded_at: datetime | None
    status: Status
    updated_at: datetime


class StatusBody(Body):
    status: Status


class ReleaseBody(Body):
    title: str = Field(min_length=1, max_length=255)
    request_text: str = Field(min_length=1, max_length=4000)

    @field_validator("title", "request_text")
    @classmethod
    def not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Write a title and the request for the client")
        return value


class ClientResponseRequestView(View):
    """The whole client allowlist. Add a field only if an auditor wrote it for the client."""

    id: str
    title: str
    request_text: str
    status: Literal["open", "responded"]
    response: str
    responded_at: datetime | None
    released_at: datetime


class ClientResponseBody(Body):
    text: str = Field(min_length=1, max_length=4000)

    @field_validator("text")
    @classmethod
    def not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Write a response before submitting")
        return value


def _auditor_engagement(db: Session, user: User, engagement_id: str) -> Engagement:
    if user.role != UserRole.AUDITOR:
        raise HTTPException(403, "Auditor access required")
    return _get_engagement(db, user, engagement_id)


def _auditor_finding(db: Session, user: User, finding_id: str) -> tuple[Engagement, Finding]:
    if user.role != UserRole.AUDITOR:
        raise HTTPException(403, "Auditor access required")
    finding = db.get(Finding, finding_id)
    # One 404 for a missing finding and for one in an engagement this auditor is not assigned to.
    engagement = _get_engagement(db, user, finding.engagement_id) if finding else None
    if finding is None or engagement is None or finding.firm_id != engagement.firm_id:
        raise HTTPException(404, "Finding not found")
    return engagement, finding


def _view(finding: Finding) -> FindingView:
    return FindingView(
        id=finding.id,
        engagement_id=finding.engagement_id,
        title=finding.title,
        rule=finding.rule,
        condition=finding.condition,
        cause=finding.cause,
        effect=finding.effect,
        recommendation=finding.recommendation,
        severity=finding.severity,  # type: ignore[arg-type]
        citations=[Citation(**c) for c in finding.citations],
        management_response=finding.management_response,
        responded_at=finding.responded_at,
        status=finding.status,  # type: ignore[arg-type]
        updated_at=finding.updated_at,
    )


def _blockers(db: Session, engagement: Engagement, finding: Finding) -> list[str]:
    out = [f"Add the {name}." for name in TEXT_FIELDS if not getattr(finding, name).strip()]
    if not finding.citations:
        out.append("Cite at least one document and page.")
        return out
    cited = {c["document"] for c in finding.citations}
    known = set()
    for document in db.scalars(
        select(Document).where(
            Document.engagement_id == engagement.id,
            Document.firm_id == engagement.firm_id,
            or_(Document.original_name.in_(cited), Document.number.in_(cited)),
        )
    ):
        known.update({document.original_name, document.number})
    out.extend(
        f"Citation “{name}” is not a document of this engagement." for name in sorted(cited - known)
    )
    return out


def _log(db: Session, engagement: Engagement, user: User, action: str, entity: str, entity_id, **d):
    db.add(
        AuditLog(
            firm_id=engagement.firm_id,
            actor_id=user.id,
            action=action,
            entity_type=entity,
            entity_id=entity_id,
            details=d,
        )
    )


def _apply(finding: Finding, body: FindingBody) -> None:
    for name in TEXT_FIELDS:
        setattr(finding, name, getattr(body, name))
    finding.severity = body.severity
    finding.citations = [c.model_dump() for c in body.citations]
    finding.updated_at = datetime.now(UTC)


# --- auditor ----------------------------------------------------------------------------


@router.get(
    "/auditor/engagements/{engagement_id}/findings",
    response_model=list[FindingView],
    response_model_by_alias=True,
)
def list_findings(engagement_id: str, db: DB, user: CurrentUser) -> list[FindingView]:
    engagement = _auditor_engagement(db, user, engagement_id)
    rows = db.scalars(
        select(Finding)
        .where(Finding.engagement_id == engagement.id, Finding.firm_id == engagement.firm_id)
        .order_by(Finding.created_at, Finding.id)
    ).all()
    return [_view(row) for row in rows]


@router.post(
    "/auditor/engagements/{engagement_id}/findings",
    response_model=FindingView,
    status_code=201,
    response_model_by_alias=True,
)
def create_finding(engagement_id: str, body: FindingBody, db: DB, user: CurrentUser) -> FindingView:
    engagement = _auditor_engagement(db, user, engagement_id)
    finding = Finding(
        firm_id=engagement.firm_id, engagement_id=engagement.id, created_by_id=user.id
    )
    _apply(finding, body)
    db.add(finding)
    db.flush()
    _log(db, engagement, user, "finding.drafted", "finding", finding.id, severity=body.severity)
    db.commit()
    return _view(finding)


@router.put(
    "/auditor/engagements/{engagement_id}/findings/{finding_record_id}",
    response_model=FindingView,
    response_model_by_alias=True,
)
def update_finding(
    engagement_id: str, finding_record_id: str, body: FindingBody, db: DB, user: CurrentUser
) -> FindingView:
    engagement = _auditor_engagement(db, user, engagement_id)
    finding = db.scalar(
        select(Finding).where(
            Finding.id == finding_record_id,
            Finding.engagement_id == engagement.id,
            Finding.firm_id == engagement.firm_id,
        )
    )
    if finding is None:
        raise HTTPException(404, "Finding not found")
    if finding.status not in {"draft", "approved"}:
        raise HTTPException(409, "An issued finding can no longer be edited.")
    was_approved = finding.status == "approved"
    _apply(finding, body)
    finding.status = "draft"  # editing an approved finding returns it to draft
    _log(db, engagement, user, "finding.edited", "finding", finding.id, was_approved=was_approved)
    db.commit()
    return _view(finding)


@router.post(
    "/auditor/findings/{finding_record_id}/status",
    response_model=FindingView,
    response_model_by_alias=True,
)
def set_status(finding_record_id: str, body: StatusBody, db: DB, user: CurrentUser) -> FindingView:
    engagement, finding = _auditor_finding(db, user, finding_record_id)
    if body.status == "issued":
        raise HTTPException(409, "Release a response request to issue a finding.")
    if body.status not in MOVES[finding.status]:
        raise HTTPException(409, f"A {finding.status} finding cannot move to {body.status}.")
    if body.status == "approved":
        blockers = _blockers(db, engagement, finding)
        if blockers:
            raise HTTPException(422, blockers[0])
    previous = finding.status
    finding.status = body.status
    finding.updated_at = datetime.now(UTC)
    _log(
        db,
        engagement,
        user,
        "finding.status_changed",
        "finding",
        finding.id,
        **{"from": previous, "to": body.status},
    )
    db.commit()
    return _view(finding)


@router.delete("/auditor/findings/{finding_record_id}", status_code=204)
def delete_draft(finding_record_id: str, db: DB, user: CurrentUser) -> None:
    engagement, finding = _auditor_finding(db, user, finding_record_id)
    if finding.status != "draft":
        raise HTTPException(409, "Only a draft finding can be deleted.")
    _log(db, engagement, user, "finding.deleted", "finding", finding.id)
    db.delete(finding)
    db.commit()


@router.post(
    "/auditor/findings/{finding_record_id}/response-request",
    response_model=FindingView,
    status_code=201,
    response_model_by_alias=True,
)
def release_response_request(
    finding_record_id: str, body: ReleaseBody, db: DB, user: CurrentUser
) -> FindingView:
    """Explicit release: the client sees only this title and text, nothing from the finding."""
    engagement, finding = _auditor_finding(db, user, finding_record_id)
    if finding.status != "approved":
        raise HTTPException(409, "Approve the finding before requesting a response.")
    blockers = _blockers(db, engagement, finding)
    if blockers:
        raise HTTPException(422, blockers[0])
    db.add(
        ResponseRequest(
            firm_id=engagement.firm_id,
            engagement_id=engagement.id,
            finding_id=finding.id,
            title=body.title,
            request_text=body.request_text,
            released_by_id=user.id,
        )
    )
    finding.status = "issued"
    finding.updated_at = datetime.now(UTC)
    db.flush()
    _log(
        db,
        engagement,
        user,
        "finding.response_released",
        "finding",
        finding.id,
        text_length=len(body.request_text),
    )
    db.commit()
    return _view(finding)


# --- client -----------------------------------------------------------------------------


def _client_engagement(db: Session, user: User, engagement_id: str) -> Engagement:
    engagement = _get_engagement(db, user, engagement_id)
    if user.role != UserRole.CLIENT:
        raise HTTPException(403, "Only firm users can do this")
    return engagement


def _client_view(row: ResponseRequest) -> ClientResponseRequestView:
    return ClientResponseRequestView(
        id=row.id,
        title=row.title,
        request_text=row.request_text,
        status=row.status,  # type: ignore[arg-type]
        response=row.response,
        responded_at=row.responded_at,
        released_at=row.released_at,
    )


def _client_list(db: Session, engagement: Engagement) -> list[ClientResponseRequestView]:
    rows = db.scalars(
        select(ResponseRequest)
        .where(
            ResponseRequest.engagement_id == engagement.id,
            ResponseRequest.firm_id == engagement.firm_id,
        )
        .order_by(ResponseRequest.released_at, ResponseRequest.id)
    ).all()
    return [_client_view(row) for row in rows]


@router.get(
    "/engagements/{engagement_id}/response-requests",
    response_model=list[ClientResponseRequestView],
    response_model_by_alias=True,
)
def client_response_requests(
    engagement_id: str, db: DB, user: CurrentUser
) -> list[ClientResponseRequestView]:
    return _client_list(db, _client_engagement(db, user, engagement_id))


@router.post(
    "/engagements/{engagement_id}/response-requests/{response_request_id}/response",
    response_model=list[ClientResponseRequestView],
    response_model_by_alias=True,
)
def respond(
    engagement_id: str,
    response_request_id: str,
    body: ClientResponseBody,
    db: DB,
    user: CurrentUser,
) -> list[ClientResponseRequestView]:
    engagement = _client_engagement(db, user, engagement_id)
    row = db.scalar(
        select(ResponseRequest).where(
            ResponseRequest.id == response_request_id,
            ResponseRequest.engagement_id == engagement.id,
            ResponseRequest.firm_id == engagement.firm_id,
        )
    )
    if row is None:
        raise HTTPException(404, "Request not found")
    if row.status != "open":
        raise HTTPException(409, "This item is not open for a response.")
    finding = db.get(Finding, row.finding_id)
    now = datetime.now(UTC)
    row.response, row.responded_at, row.responded_by_id, row.status = (
        body.text,
        now,
        user.id,
        "responded",
    )
    if finding is not None and finding.firm_id == engagement.firm_id and finding.status == "issued":
        finding.management_response, finding.responded_at = body.text, now
        finding.status, finding.updated_at = "responded", now
    _log(
        db,
        engagement,
        user,
        "response_request.responded",
        "response_request",
        row.id,
        text_length=len(body.text),
    )
    db.commit()
    return _client_list(db, engagement)
