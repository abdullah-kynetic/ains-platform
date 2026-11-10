"""Quentin's workflow routes: dispatch, reasoned N/A, links, submit, issue threads, report.

Every route resolves the engagement through ``visible_engagements`` (auditors: assigned only;
clients: their own firm only) and filters child rows by ``firm_id`` and ``engagement_id``.
Role checks here are server-side authorization. Clients never receive findings, internal
notes, assessments or check results; thread messages are the text an auditor wrote for the
client about a document.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.alias_generators import to_camel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.checklist import ClientStatus
from app.checklist.applicability import record_na_change
from app.checklist.catalog import load_catalog
from app.database.models import (
    AuditLog,
    ChecklistItemInstance,
    Document,
    DocumentIssue,
    DocumentItemLink,
    Engagement,
    EngagementReport,
    EngagementStatus,
    IssueMessage,
    NAReviewState,
    User,
    UserRole,
)
from app.reports import ReportGenerator
from app.workflow import (
    ISSUE_KINDS,
    ISSUE_REASON,
    checklist_sent,
    item_documents,
    progress,
    workflow_stage,
)

from .engagements import DB, CurrentUser
from .intake import intake_item
from .questionnaire import _get_engagement

router = APIRouter(tags=["workflow"])


class Body(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="forbid")


def _auditor(user: User) -> None:
    if user.role != UserRole.AUDITOR:
        raise HTTPException(403, "Auditor access required")


def _client(user: User) -> None:
    if user.role != UserRole.CLIENT:
        raise HTTPException(403, "Only firm users can do this")


def _log(db: Session, engagement: Engagement, user: User, action, entity_type, entity_id, **d):
    db.add(
        AuditLog(
            firm_id=engagement.firm_id,
            actor_id=user.id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=d,
        )
    )


def _item(db: Session, user: User, engagement_id: str, item_id: str):
    engagement, item = intake_item(db, user, engagement_id, item_id)
    return engagement, item


def _require_open_engagement(engagement: Engagement) -> None:
    if engagement.status in {EngagementStatus.DRAFT, EngagementStatus.COMPLETE}:
        raise HTTPException(409, "Engagement is not accepting client work")


def _active_item(item: ChecklistItemInstance) -> None:
    definition = load_catalog().get(item.item_key)
    if definition is None or item.restricted or definition.restricted:
        raise HTTPException(409, "This restricted item must be handled directly with the auditor")
    if not item.applicable or item.status == ClientStatus.NOT_APPLICABLE:
        raise HTTPException(409, "This request is not active")


# --- dispatch -----------------------------------------------------------------------------


@router.post("/auditor/engagements/{engagement_id}/checklist/send")
def send_checklist(engagement_id: str, user: CurrentUser, db: DB):
    """Record the dispatch of the numbered checklist to the client. Initialization is not it."""
    _auditor(user)
    engagement = _get_engagement(db, user, engagement_id)
    if engagement.checklist_sent_at is not None:
        raise HTTPException(409, "The checklist was already sent")
    count = db.scalar(
        select(func.count())
        .select_from(ChecklistItemInstance)
        .where(
            ChecklistItemInstance.engagement_id == engagement.id,
            ChecklistItemInstance.firm_id == engagement.firm_id,
        )
    )
    if not count:
        raise HTTPException(409, "Initialize the checklist before sending it")
    before = engagement.status
    engagement.checklist_sent_at = datetime.now(UTC)
    engagement.checklist_sent_by_id = user.id
    if engagement.status == EngagementStatus.DRAFT:
        engagement.status = EngagementStatus.COLLECTING
    _log(
        db, engagement, user, "checklist.sent", "engagement", engagement.id,
        before={"status": before}, after={"status": engagement.status}, items=count,
    )  # fmt: skip
    db.commit()
    return {
        "sentAt": engagement.checklist_sent_at,
        "stage": workflow_stage(db, engagement),
    }


# --- progress -----------------------------------------------------------------------------


@router.get("/auditor/engagements/{engagement_id}/progress")
def auditor_progress(engagement_id: str, user: CurrentUser, db: DB):
    _auditor(user)
    return progress(db, _get_engagement(db, user, engagement_id))


@router.get("/engagements/{engagement_id}/progress")
def client_progress(engagement_id: str, user: CurrentUser, db: DB):
    _client(user)
    return progress(db, _get_engagement(db, user, engagement_id))


# --- reasoned N/A -------------------------------------------------------------------------


class NARequest(Body):
    reason: str = Field(min_length=5, max_length=1000)

    @field_validator("reason")
    @classmethod
    def clean(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 5:
            raise ValueError("Give a reason of at least 5 characters")
        return value


class NADecision(Body):
    decision: Literal["accept", "reject"]
    note: str | None = Field(default=None, max_length=1000)


@router.post("/engagements/{engagement_id}/items/{item_id}/na-request")
def request_na(engagement_id: str, item_id: str, payload: NARequest, user: CurrentUser, db: DB):
    """Client asks for N/A with a required reason. Nothing changes until an auditor decides."""
    _client(user)
    engagement, item = _item(db, user, engagement_id, item_id)
    _require_open_engagement(engagement)
    _active_item(item)
    if item.na_review_state == NAReviewState.PENDING:
        raise HTTPException(409, "An N/A request is already waiting for the auditor")
    before = item.na_review_state
    item.na_review_state = NAReviewState.PENDING
    item.na_request_reason = payload.reason
    item.na_requested_at = datetime.now(UTC)
    item.na_decision_note = None
    item.na_decided_at = None
    _log(
        db, engagement, user, "request.na_requested", "checklist_item_instance", item.id,
        before={"na_review_state": before}, reason_length=len(payload.reason),
    )  # fmt: skip
    db.commit()
    return {"state": "pending"}


@router.post("/auditor/engagements/{engagement_id}/items/{item_id}/na-request/decision")
def decide_na_request(
    engagement_id: str, item_id: str, payload: NADecision, user: CurrentUser, db: DB
):
    """Accept (item becomes N/A, sorts last, number kept; undo restores) or reject with a note."""
    _auditor(user)
    engagement, item = _item(db, user, engagement_id, item_id)
    db.refresh(item, with_for_update=True)
    if item.na_review_state != NAReviewState.PENDING:
        raise HTTPException(409, "There is no pending N/A request")
    note = (payload.note or "").strip() or None
    if payload.decision == "reject" and not note:
        raise HTTPException(422, "Explain the rejection so the client can respond")
    if payload.decision == "accept":
        record_na_change(db, item, user, True)
    else:
        item.na_review_state = NAReviewState.REJECTED
        item.na_approved_by_id = user.id
    item.na_decision_note = note
    item.na_decided_at = datetime.now(UTC)
    _log(
        db, engagement, user, f"request.na_{payload.decision}ed", "checklist_item_instance",
        item.id, decision=payload.decision, note_length=len(note or ""),
    )  # fmt: skip
    db.commit()
    return {"state": "accepted" if payload.decision == "accept" else "rejected"}


# --- documents: link and submit -----------------------------------------------------------


def _engagement_document(db: Session, engagement: Engagement, document_id: str) -> Document:
    document = db.scalar(
        select(Document).where(
            Document.id == document_id,
            Document.engagement_id == engagement.id,
            Document.firm_id == engagement.firm_id,
        )
    )
    if document is None:
        raise HTTPException(404, "Document not found")
    return document


@router.post("/engagements/{engagement_id}/items/{item_id}/documents/{document_id}/link")
def link_document(engagement_id: str, item_id: str, document_id: str, user: CurrentUser, db: DB):
    """Client links an uploaded receipt to an item ("Item 22: see 1.17")."""
    _client(user)
    engagement, item = _item(db, user, engagement_id, item_id)
    _require_open_engagement(engagement)
    _active_item(item)
    document = _engagement_document(db, engagement, document_id)
    existing = db.scalar(
        select(DocumentItemLink).where(
            DocumentItemLink.item_instance_id == item.id,
            DocumentItemLink.document_id == document.id,
            DocumentItemLink.firm_id == engagement.firm_id,
        )
    )
    if existing is None and document.item_instance_id != item.id:
        db.add(
            DocumentItemLink(
                firm_id=engagement.firm_id,
                engagement_id=engagement.id,
                item_instance_id=item.id,
                document_id=document.id,
                linked_by_id=user.id,
            )
        )
        _log(
            db, engagement, user, "document.linked", "checklist_item_instance", item.id,
            document_id=document.id, number=document.number,
        )  # fmt: skip
        db.commit()
    return {"itemId": item.id, "documentId": document.id, "number": document.number}


@router.delete("/engagements/{engagement_id}/items/{item_id}/documents/{document_id}/link")
def unlink_document(engagement_id: str, item_id: str, document_id: str, user: CurrentUser, db: DB):
    _client(user)
    engagement, item = _item(db, user, engagement_id, item_id)
    _require_open_engagement(engagement)
    link = db.scalar(
        select(DocumentItemLink).where(
            DocumentItemLink.item_instance_id == item.id,
            DocumentItemLink.document_id == document_id,
            DocumentItemLink.firm_id == engagement.firm_id,
            DocumentItemLink.engagement_id == engagement.id,
        )
    )
    if link is None:
        raise HTTPException(404, "Link not found")
    db.delete(link)
    _log(
        db, engagement, user, "document.unlinked", "checklist_item_instance", item.id,
        document_id=document_id,
    )  # fmt: skip
    db.commit()
    return {"itemId": item.id, "documentId": document_id}


def _submit(db: Session, engagement: Engagement, item: ChecklistItemInstance, user: User) -> bool:
    docs = item_documents(db, engagement).get(item.id, [])
    if not docs:
        return False
    item.submitted_at = datetime.now(UTC)
    item.submitted_by_id = user.id
    if item.status in {
        ClientStatus.REQUESTED,
        ClientStatus.ACTION_NEEDED_REUPLOAD,
        ClientStatus.ACTION_NEEDED_MORE,
    }:
        item.status = ClientStatus.WITH_AUDITOR
        item.client_reason = None
    _log(
        db, engagement, user, "request.submitted", "checklist_item_instance", item.id,
        documents=[d.number for d in docs],
    )  # fmt: skip
    return True


def _open_issues(db: Session, engagement: Engagement, item_id: str) -> int:
    return (
        db.scalar(
            select(func.count())
            .select_from(DocumentIssue)
            .where(
                DocumentIssue.item_instance_id == item_id,
                DocumentIssue.engagement_id == engagement.id,
                DocumentIssue.firm_id == engagement.firm_id,
                DocumentIssue.status == "open",
            )
        )
        or 0
    )


@router.post("/engagements/{engagement_id}/items/{item_id}/submit")
def submit_item(engagement_id: str, item_id: str, user: CurrentUser, db: DB):
    """Client submits one item for review. It needs at least one uploaded or linked document."""
    _client(user)
    engagement, item = _item(db, user, engagement_id, item_id)
    _require_open_engagement(engagement)
    _active_item(item)
    if item.na_review_state == NAReviewState.PENDING:
        raise HTTPException(409, "Wait for the auditor to decide the N/A request first")
    if _open_issues(db, engagement, item.id):
        raise HTTPException(409, "Answer the open request thread for this item first")
    if not _submit(db, engagement, item, user):
        raise HTTPException(409, "Upload or link at least one document first")
    db.commit()
    return {"itemId": item.id, "status": "submitted"}


@router.post("/engagements/{engagement_id}/submit")
def submit_checklist(engagement_id: str, user: CurrentUser, db: DB):
    """Client submits the checklist: every ready item is submitted, the rest are listed."""
    _client(user)
    engagement = _get_engagement(db, user, engagement_id)
    _require_open_engagement(engagement)
    items = db.scalars(
        select(ChecklistItemInstance).where(
            ChecklistItemInstance.engagement_id == engagement.id,
            ChecklistItemInstance.firm_id == engagement.firm_id,
        )
    ).all()
    submitted, skipped = [], []
    for item in items:
        if (
            item.restricted
            or not item.applicable
            or item.status == ClientStatus.NOT_APPLICABLE
            or item.na_review_state == NAReviewState.PENDING
        ):
            continue
        if _open_issues(db, engagement, item.id) or not _submit(db, engagement, item, user):
            skipped.append(item.item_key)
        else:
            submitted.append(item.item_key)
    if not submitted:
        raise HTTPException(409, "No item has a document to submit yet")
    engagement.client_submitted_at = engagement.client_submitted_at or datetime.now(UTC)
    _log(
        db, engagement, user, "checklist.submitted", "engagement", engagement.id,
        submitted=len(submitted), skipped=len(skipped),
    )  # fmt: skip
    db.commit()
    return {"submitted": submitted, "notReady": skipped, "stage": workflow_stage(db, engagement)}


@router.post("/auditor/engagements/{engagement_id}/items/{item_id}/accept")
def accept_item(engagement_id: str, item_id: str, user: CurrentUser, db: DB):
    """Auditor accepts the item's documents for testing. Not an audit result."""
    _auditor(user)
    engagement, item = _item(db, user, engagement_id, item_id)
    _active_item(item)
    if item.submitted_at is None:
        raise HTTPException(409, "The client has not submitted this item")
    if _open_issues(db, engagement, item.id):
        raise HTTPException(409, "Resolve the open request threads first")
    before = item.status
    item.status = ClientStatus.ACCEPTED_FOR_TESTING
    item.client_reason = None
    _log(
        db, engagement, user, "request.accepted", "checklist_item_instance", item.id,
        before={"status": before}, after={"status": item.status},
    )  # fmt: skip
    db.commit()
    return {"itemId": item.id, "status": "accepted"}


# --- issue flags and request threads ------------------------------------------------------


class FlagInput(Body):
    kind: Literal["outdated", "wrong_year", "incorrect", "missing"]
    document_id: str | None = Field(default=None, max_length=36)
    note: str = Field(min_length=1, max_length=2000)

    @field_validator("note")
    @classmethod
    def clean(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Write the request for the client")
        return value


class ReplyInput(Body):
    body: str = Field(min_length=1, max_length=2000)
    document_id: str | None = Field(default=None, max_length=36)

    @field_validator("body")
    @classmethod
    def clean(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Write a reply")
        return value


class ResolveInput(Body):
    note: str | None = Field(default=None, max_length=2000)


def _issue_view(issue: DocumentIssue, db: Session) -> dict[str, object]:
    numbers = {
        d.id: d.number
        for d in db.scalars(
            select(Document).where(
                Document.id.in_(
                    [m.document_id for m in issue.messages if m.document_id]
                    + ([issue.document_id] if issue.document_id else [])
                ),
                Document.firm_id == issue.firm_id,
            )
        )
    }
    return {
        "id": issue.id,
        "itemId": issue.item_instance_id,
        "kind": issue.kind,
        "status": issue.status,
        "document": (
            {"id": issue.document_id, "number": numbers.get(issue.document_id)}
            if issue.document_id
            else None
        ),
        "createdAt": issue.created_at,
        "resolvedAt": issue.resolved_at,
        "awaiting": (
            None
            if issue.status == "resolved"
            else ("auditor" if issue.messages[-1].author_role == "client" else "client")
        ),
        "messages": [
            {
                "id": m.id,
                "authorRole": m.author_role,
                "body": m.body,
                "documentNumber": numbers.get(m.document_id) if m.document_id else None,
                "createdAt": m.created_at,
            }
            for m in issue.messages
        ],
    }


def _issues(db: Session, engagement: Engagement, item_id: str | None = None):
    query = select(DocumentIssue).where(
        DocumentIssue.engagement_id == engagement.id, DocumentIssue.firm_id == engagement.firm_id
    )
    if item_id:
        query = query.where(DocumentIssue.item_instance_id == item_id)
    return db.scalars(query.order_by(DocumentIssue.created_at, DocumentIssue.id)).all()


def _issue(db: Session, engagement: Engagement, issue_id: str) -> DocumentIssue:
    issue = db.scalar(
        select(DocumentIssue)
        .where(
            DocumentIssue.id == issue_id,
            DocumentIssue.engagement_id == engagement.id,
            DocumentIssue.firm_id == engagement.firm_id,
        )
        .with_for_update()
    )
    if issue is None:
        raise HTTPException(404, "Request thread not found")
    return issue


@router.post("/auditor/engagements/{engagement_id}/items/{item_id}/issues", status_code=201)
def flag_document(engagement_id: str, item_id: str, payload: FlagInput, user: CurrentUser, db: DB):
    """Atomically flag a document (or a missing one) and open the item's request thread."""
    _auditor(user)
    engagement, item = _item(db, user, engagement_id, item_id)
    _active_item(item)
    if payload.kind not in ISSUE_KINDS:  # pragma: no cover - the schema already enforces it
        raise HTTPException(422, "Unknown flag")
    document_id = None
    if payload.kind != "missing" or payload.document_id:
        if not payload.document_id:
            raise HTTPException(422, "Choose the document to flag")
        document = _engagement_document(db, engagement, payload.document_id)
        if document.id not in {d.id for d in item_documents(db, engagement).get(item.id, [])}:
            raise HTTPException(404, "Document not found")
        document_id = document.id
    issue = DocumentIssue(
        firm_id=engagement.firm_id,
        engagement_id=engagement.id,
        item_instance_id=item.id,
        document_id=document_id,
        kind=payload.kind,
        created_by_id=user.id,
    )
    db.add(issue)
    db.flush()
    db.add(
        IssueMessage(
            firm_id=engagement.firm_id,
            issue_id=issue.id,
            author_id=user.id,
            author_role="auditor",
            body=payload.note,
        )
    )
    before = item.status
    item.status = (
        ClientStatus.ACTION_NEEDED_MORE
        if payload.kind == "missing"
        else ClientStatus.ACTION_NEEDED_REUPLOAD
    )
    item.assessment = None
    item.client_reason = ISSUE_REASON[payload.kind]
    _log(
        db, engagement, user, "document.issue_flagged", "checklist_item_instance", item.id,
        issue_id=issue.id, kind=payload.kind, document_id=document_id,
        note_length=len(payload.note), before={"status": before}, after={"status": item.status},
    )  # fmt: skip
    db.commit()
    db.refresh(issue)
    return _issue_view(issue, db)


@router.get("/auditor/engagements/{engagement_id}/issues")
def auditor_issues(engagement_id: str, user: CurrentUser, db: DB):
    _auditor(user)
    engagement = _get_engagement(db, user, engagement_id)
    return [_issue_view(i, db) for i in _issues(db, engagement)]


@router.get("/engagements/{engagement_id}/issues")
def client_issues(engagement_id: str, user: CurrentUser, db: DB):
    _client(user)
    engagement = _get_engagement(db, user, engagement_id)
    return [_issue_view(i, db) for i in _issues(db, engagement)]


def _reply(
    db: Session, engagement: Engagement, user: User, issue_id: str, payload: ReplyInput
) -> dict[str, object]:
    issue = _issue(db, engagement, issue_id)
    if issue.status != "open":
        raise HTTPException(409, "This request thread is resolved")
    role = user.role.value
    document_id = None
    if payload.document_id:
        document = _engagement_document(db, engagement, payload.document_id)
        document_id = document.id
        if (
            user.role == UserRole.CLIENT
            and document.item_instance_id != issue.item_instance_id
            and not db.scalar(
                select(DocumentItemLink.id).where(
                    DocumentItemLink.item_instance_id == issue.item_instance_id,
                    DocumentItemLink.document_id == document.id,
                )
            )
        ):
            # A re-upload attached to a reply is linked to the item so both sides see it.
            db.add(
                DocumentItemLink(
                    firm_id=engagement.firm_id,
                    engagement_id=engagement.id,
                    item_instance_id=issue.item_instance_id,
                    document_id=document.id,
                    linked_by_id=user.id,
                )
            )
    db.add(
        IssueMessage(
            firm_id=engagement.firm_id,
            issue_id=issue.id,
            author_id=user.id,
            author_role=role,
            body=payload.body,
            document_id=document_id,
        )
    )
    if user.role == UserRole.CLIENT:
        item = db.get(ChecklistItemInstance, issue.item_instance_id)
        if item is not None and item.firm_id == engagement.firm_id:
            item.status = ClientStatus.WITH_AUDITOR
            item.submitted_at = item.submitted_at or datetime.now(UTC)
    _log(
        db, engagement, user, "issue.replied", "document_issue", issue.id,
        author_role=role, body_length=len(payload.body), document_id=document_id,
    )  # fmt: skip
    db.commit()
    db.refresh(issue)
    return _issue_view(issue, db)


@router.post("/engagements/{engagement_id}/issues/{issue_id}/replies", status_code=201)
def client_reply(engagement_id: str, issue_id: str, payload: ReplyInput, user: CurrentUser, db: DB):
    _client(user)
    return _reply(db, _get_engagement(db, user, engagement_id), user, issue_id, payload)


@router.post("/auditor/engagements/{engagement_id}/issues/{issue_id}/replies", status_code=201)
def auditor_reply(
    engagement_id: str, issue_id: str, payload: ReplyInput, user: CurrentUser, db: DB
):
    _auditor(user)
    return _reply(db, _get_engagement(db, user, engagement_id), user, issue_id, payload)


@router.post("/auditor/engagements/{engagement_id}/issues/{issue_id}/resolve")
def resolve_issue(
    engagement_id: str, issue_id: str, payload: ResolveInput, user: CurrentUser, db: DB
):
    """Explicit resolution. Only the auditor can close a thread; that drives item status."""
    _auditor(user)
    engagement = _get_engagement(db, user, engagement_id)
    issue = _issue(db, engagement, issue_id)
    if issue.status != "open":
        raise HTTPException(409, "This request thread is already resolved")
    note = (payload.note or "").strip()
    if note:
        db.add(
            IssueMessage(
                firm_id=engagement.firm_id,
                issue_id=issue.id,
                author_id=user.id,
                author_role="auditor",
                body=note,
            )
        )
    issue.status = "resolved"
    issue.resolved_by_id = user.id
    issue.resolved_at = datetime.now(UTC)
    db.flush()
    item = db.get(ChecklistItemInstance, issue.item_instance_id)
    if item is not None and item.firm_id == engagement.firm_id:
        if not _open_issues(db, engagement, item.id) and item.status in {
            ClientStatus.ACTION_NEEDED_REUPLOAD,
            ClientStatus.ACTION_NEEDED_MORE,
            ClientStatus.WITH_AUDITOR,
        }:
            has_documents = bool(item_documents(db, engagement).get(item.id))
            item.status = ClientStatus.WITH_AUDITOR if has_documents else ClientStatus.REQUESTED
            item.client_reason = None
    _log(
        db, engagement, user, "issue.resolved", "document_issue", issue.id,
        kind=issue.kind, note_length=len(note),
    )  # fmt: skip
    db.commit()
    db.refresh(issue)
    return _issue_view(issue, db)


# --- client report confirmation -----------------------------------------------------------


class ConfirmReport(Body):
    content_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")


def _final_report(db: Session, engagement: Engagement) -> EngagementReport:
    report = db.scalar(
        select(EngagementReport).where(
            EngagementReport.engagement_id == engagement.id,
            EngagementReport.firm_id == engagement.firm_id,
            EngagementReport.status == "final",
        )
    )
    if report is None:
        raise HTTPException(404, "No finalized report")
    return report


def _client_report_view(engagement: Engagement, report: EngagementReport) -> dict[str, object]:
    # Allowlist: the human-authored sections and the hash. Item findings, the status snapshot
    # and internal fields are never sent to the client.
    sections = report.content.get("sections", []) if isinstance(report.content, dict) else []
    # Clients never see findings: the findings section is withheld until Abdullah decides.
    hidden = ReportGenerator().template.findings_heading.strip().casefold()
    sections = [s for s in sections if str(s.get("title", "")).strip().casefold() != hidden]
    return {
        "engagementId": engagement.id,
        "reportId": report.id,
        "sections": [{"title": s.get("title"), "html": s.get("html")} for s in sections],
        "finalizedAt": report.finalized_at,
        "contentSha256": report.content_sha256,
        "confirmed": engagement.report_confirmed_at is not None,
        "confirmedAt": engagement.report_confirmed_at,
    }


@router.get("/engagements/{engagement_id}/report")
def client_report(engagement_id: str, user: CurrentUser, db: DB):
    _client(user)
    engagement = _get_engagement(db, user, engagement_id)
    report = _final_report(db, engagement)
    _log(db, engagement, user, "report.viewed", "engagement_report", report.id)
    db.commit()
    return _client_report_view(engagement, report)


@router.post("/engagements/{engagement_id}/report/confirm")
def confirm_report(engagement_id: str, payload: ConfirmReport, user: CurrentUser, db: DB):
    """Client confirms the exact finalized report (by hash). Audit-logged; enables invoicing."""
    _client(user)
    engagement = _get_engagement(db, user, engagement_id)
    report = _final_report(db, engagement)
    if payload.content_sha256 != report.content_sha256:
        raise HTTPException(409, "The report changed. Reload it and confirm again.")
    if engagement.report_confirmed_at is None:
        engagement.report_confirmed_at = datetime.now(UTC)
        engagement.report_confirmed_by_id = user.id
        engagement.report_confirmed_sha256 = report.content_sha256
        _log(
            db, engagement, user, "report.confirmed", "engagement_report", report.id,
            content_sha256=report.content_sha256, version=report.version,
        )  # fmt: skip
        db.commit()
    return _client_report_view(engagement, report)


__all__ = ["checklist_sent", "router"]
