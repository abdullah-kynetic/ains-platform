"""Workflow rules for the numbered checklist: dispatch, item state, document numbers, stages.

Everything here is derived from recorded human actions. Nothing is inferred by a model and no
audit conclusion is produced: "accepted" means an auditor accepted the item's documents for
testing, not that the firm passed.
"""

from __future__ import annotations

from typing import Literal

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.checklist import ClientStatus
from app.checklist.catalog import load_catalog
from app.database.models import (
    ChecklistItemInstance,
    Document,
    DocumentIssue,
    DocumentItemLink,
    Engagement,
    EngagementReport,
    EngagementStatus,
    Invoice,
    NAReviewState,
)

ItemState = Literal["not_started", "submitted", "needs_info", "accepted", "na", "restricted"]
WorkflowStage = Literal[
    "not_sent",
    "checklist_sent",
    "client_working",
    "under_review",
    "info_requested",
    "report_drafting",
    "report_sent",
    "confirmed",
    "invoiced",
    "paid",
]
ISSUE_KINDS = ("outdated", "wrong_year", "incorrect", "missing")
# Neutral, document-only text shown in the client's item reason. The auditor's own message is
# the thread's first entry; this text never carries audit conclusions.
ISSUE_REASON = {
    "outdated": "A document for this request is out of date. Please see the request thread.",
    "wrong_year": "A document for this request covers the wrong year. See the request thread.",
    "incorrect": "A document for this request needs correcting. See the request thread.",
    "missing": "A document for this request is missing. Please see the request thread.",
}
DOCUMENT_SERIES = 1


def item_numbers() -> dict[str, int]:
    """Original item numbers (1-based catalog order). They never change, even for N/A items."""
    return {request.id: index + 1 for index, request in enumerate(load_catalog().requests)}


def allocate_document_number(db: Session, engagement: Engagement) -> str:
    """Next stable document number such as ``1.17``; atomic, never reused or renumbered."""
    db.execute(
        update(Engagement)
        .where(Engagement.id == engagement.id, Engagement.firm_id == engagement.firm_id)
        .values(document_seq=Engagement.document_seq + 1)
    )
    sequence = db.scalar(
        select(Engagement.document_seq).where(
            Engagement.id == engagement.id, Engagement.firm_id == engagement.firm_id
        )
    )
    db.refresh(engagement, ["document_seq"])
    return f"{DOCUMENT_SERIES}.{sequence}"


def checklist_sent(engagement: Engagement) -> bool:
    return engagement.checklist_sent_at is not None or engagement.status != EngagementStatus.DRAFT


def open_issue_counts(db: Session, engagement: Engagement) -> dict[str, int]:
    rows = db.execute(
        select(DocumentIssue.item_instance_id, func.count())
        .where(
            DocumentIssue.engagement_id == engagement.id,
            DocumentIssue.firm_id == engagement.firm_id,
            DocumentIssue.status == "open",
        )
        .group_by(DocumentIssue.item_instance_id)
    ).all()
    return {item_id: count for item_id, count in rows}


def item_state(item: ChecklistItemInstance, open_issues: int) -> ItemState:
    if item.status == ClientStatus.NOT_APPLICABLE:
        return "na"
    if item.restricted or item.status == ClientStatus.RESTRICTED_DO_NOT_UPLOAD:
        return "restricted"
    if open_issues or item.status in {
        ClientStatus.ACTION_NEEDED_REUPLOAD,
        ClientStatus.ACTION_NEEDED_MORE,
    }:
        return "needs_info"
    if item.status == ClientStatus.ACCEPTED_FOR_TESTING:
        return "accepted"
    if item.submitted_at is not None:
        return "submitted"
    return "not_started"


def na_request_state(item: ChecklistItemInstance) -> str | None:
    """Client-facing N/A request state: pending, accepted or rejected."""
    state = item.na_review_state
    if state is None:
        return None
    return {
        NAReviewState.PENDING: "pending",
        NAReviewState.APPROVED: "accepted",
        NAReviewState.REJECTED: "rejected",
    }[state]


def item_documents(db: Session, engagement: Engagement) -> dict[str, list[Document]]:
    """Documents per item: uploaded under the item, plus client-made links."""
    by_item: dict[str, dict[str, Document]] = {}
    uploaded = db.scalars(
        select(Document)
        .where(
            Document.engagement_id == engagement.id,
            Document.firm_id == engagement.firm_id,
            Document.item_instance_id.is_not(None),
        )
        .order_by(Document.created_at, Document.id)
    ).all()
    for document in uploaded:
        by_item.setdefault(document.item_instance_id, {})[document.id] = document
    linked = db.execute(
        select(DocumentItemLink.item_instance_id, Document)
        .join(Document, Document.id == DocumentItemLink.document_id)
        .where(
            DocumentItemLink.engagement_id == engagement.id,
            DocumentItemLink.firm_id == engagement.firm_id,
            Document.firm_id == engagement.firm_id,
        )
        .order_by(DocumentItemLink.created_at, DocumentItemLink.id)
    ).all()
    for item_id, document in linked:
        by_item.setdefault(item_id, {}).setdefault(document.id, document)
    return {item_id: list(docs.values()) for item_id, docs in by_item.items()}


def workflow_stage(db: Session, engagement: Engagement) -> WorkflowStage:
    """The furthest recorded step of the engagement, derived from stored facts."""
    invoice_statuses = set(
        db.scalars(
            select(Invoice.status).where(
                Invoice.engagement_id == engagement.id, Invoice.firm_id == engagement.firm_id
            )
        )
    )
    if "paid" in invoice_statuses:
        return "paid"
    if "sent" in invoice_statuses:
        return "invoiced"
    if engagement.report_confirmed_at is not None:
        return "confirmed"
    report_status = db.scalar(
        select(EngagementReport.status).where(
            EngagementReport.engagement_id == engagement.id,
            EngagementReport.firm_id == engagement.firm_id,
        )
    )
    if report_status == "final":
        return "report_sent"
    if report_status == "draft" or engagement.status in {
        EngagementStatus.REPORT_DRAFTING,
        EngagementStatus.AWAITING_SIGNATURE,
        EngagementStatus.COMPLETE,
    }:
        return "report_drafting"
    if not checklist_sent(engagement):
        return "not_sent"
    if open_issue_counts(db, engagement):
        return "info_requested"
    items = db.scalars(
        select(ChecklistItemInstance).where(
            ChecklistItemInstance.engagement_id == engagement.id,
            ChecklistItemInstance.firm_id == engagement.firm_id,
        )
    ).all()
    if engagement.client_submitted_at is not None or any(i.submitted_at for i in items):
        return "under_review"
    activity = (
        any(i.na_review_state is not None or i.documents for i in items)
        or db.scalar(
            select(func.count())
            .select_from(Document)
            .where(Document.engagement_id == engagement.id, Document.firm_id == engagement.firm_id)
        )
        or 0
    )
    return "client_working" if activity else "checklist_sent"


def progress(db: Session, engagement: Engagement) -> dict[str, object]:
    """Per-item status and totals. Every field is safe for the client and the auditor."""
    numbers = item_numbers()
    open_issues = open_issue_counts(db, engagement)
    documents = item_documents(db, engagement)
    items = db.scalars(
        select(ChecklistItemInstance).where(
            ChecklistItemInstance.engagement_id == engagement.id,
            ChecklistItemInstance.firm_id == engagement.firm_id,
        )
    ).all()
    rows = []
    counts = {
        "not_started": 0,
        "submitted": 0,
        "needs_info": 0,
        "accepted": 0,
        "na": 0,
        "restricted": 0,
        "na_pending": 0,
    }
    for item in items:
        number = numbers.get(item.item_key)
        if number is None:
            continue
        state = item_state(item, open_issues.get(item.id, 0))
        # A pending N/A request does not change the item's own state until accepted.
        pending = item.na_review_state == NAReviewState.PENDING and state != "na"
        counts[state] += 1
        counts["na_pending"] += int(pending)
        rows.append(
            {
                "id": item.id,
                "number": number,
                "requestId": item.item_key,
                "title": item.title,
                "status": state,
                "openIssues": open_issues.get(item.id, 0),
                "naRequest": (
                    {
                        "state": na_request_state(item),
                        "reason": item.na_request_reason,
                        "decisionNote": item.na_decision_note,
                        "requestedAt": item.na_requested_at,
                    }
                    if item.na_request_reason is not None
                    else None
                ),
                "documents": [
                    {"id": d.id, "number": d.number, "name": d.original_name}
                    for d in documents.get(item.id, [])
                ],
            }
        )
    # N/A items sort last; original numbers are kept.
    rows.sort(key=lambda row: (row["status"] == "na", row["number"]))
    total = len(rows) - counts["restricted"]
    done_submitted = counts["submitted"] + counts["accepted"] + counts["na"]
    done_accepted = counts["accepted"] + counts["na"]
    return {
        "engagementId": engagement.id,
        "stage": workflow_stage(db, engagement),
        "checklistSentAt": engagement.checklist_sent_at,
        "clientSubmittedAt": engagement.client_submitted_at,
        "reportConfirmedAt": engagement.report_confirmed_at,
        "counts": {
            "total": total,
            "notStarted": counts["not_started"],
            "submitted": counts["submitted"],
            "needsInfo": counts["needs_info"],
            "accepted": counts["accepted"],
            "notApplicable": counts["na"],
            "naPending": counts["na_pending"],
        },
        "percentSubmitted": round(done_submitted / total * 100) if total else 0,
        "percentAccepted": round(done_accepted / total * 100) if total else 0,
        "items": rows,
    }
