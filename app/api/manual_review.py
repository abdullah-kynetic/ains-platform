"""Assigned-auditor manual workflow. No inference or client-facing conclusions."""

import re
from datetime import date
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.checklist import ClientStatus
from app.checklist.catalog import initialize_engagement, load_catalog
from app.database.models import (
    AuditLog,
    AuditorTask,
    ChecklistItemInstance,
    Document,
    Engagement,
    EngagementStatus,
    FindingDraft,
    Firm,
    NAReviewState,
    TaskPriority,
    User,
    UserRole,
    utcnow,
)

from .engagements import DB, CurrentUser, visible_engagements
from .intake import intake_item
from .questionnaire import _get_engagement

router = APIRouter(prefix="/auditor", tags=["manual review"])

PipelineStage = Literal[
    "intake",
    "document_collection",
    "auditor_review",
    "report_drafting",
    "awaiting_signature",
    "complete",
]

PIPELINE_STATUS_TO_STAGE: dict[EngagementStatus, PipelineStage] = {
    EngagementStatus.DRAFT: "intake",
    EngagementStatus.COLLECTING: "document_collection",
    EngagementStatus.TESTING: "auditor_review",
    EngagementStatus.AUDITOR_REVIEW: "auditor_review",
    EngagementStatus.REPORT_DRAFTING: "report_drafting",
    EngagementStatus.AWAITING_SIGNATURE: "awaiting_signature",
    EngagementStatus.COMPLETE: "complete",
}
PIPELINE_STAGE_TO_STATUS: dict[PipelineStage, EngagementStatus] = {
    "intake": EngagementStatus.DRAFT,
    "document_collection": EngagementStatus.COLLECTING,
    "auditor_review": EngagementStatus.AUDITOR_REVIEW,
    "report_drafting": EngagementStatus.REPORT_DRAFTING,
    "awaiting_signature": EngagementStatus.AWAITING_SIGNATURE,
    "complete": EngagementStatus.COMPLETE,
}


def require_auditor(user):
    if user.role != UserRole.AUDITOR:
        raise HTTPException(403, "Auditor access required")


class ManualDecision(BaseModel):
    applicability: Literal["applicable", "not_applicable"]
    assessment: Literal["supported", "partial", "conflicting", "unable_to_determine"] | None
    notes: str = Field(max_length=5000)

    @model_validator(mode="after")
    def consistent(self):
        if self.applicability == "not_applicable" and self.assessment is not None:
            raise ValueError("A non-applicable request must not carry an evidence assessment")
        if self.applicability == "applicable" and self.assessment is None:
            raise ValueError("Choose an evidence assessment for an applicable request")
        if (
            self.applicability == "not_applicable" or self.assessment != "supported"
        ) and not self.notes.strip():
            raise ValueError("Document the reason for this decision in internal notes")
        return self


class PipelineMove(BaseModel):
    stage: PipelineStage


class WorkspaceCreate(BaseModel):
    firm_name: str = Field(min_length=2, max_length=255)
    review_period_start: date
    review_period_end: date
    due_date: date | None = None

    @model_validator(mode="after")
    def valid_workspace(self):
        self.firm_name = self.firm_name.strip()
        if len(self.firm_name) < 2:
            raise ValueError("Firm name is required")
        if self.review_period_end < self.review_period_start:
            raise ValueError("Review period end must be on or after its start")
        return self


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    request_id: str | None = Field(default=None, max_length=120)
    due_date: date | None = None
    priority: TaskPriority = TaskPriority.NORMAL

    @model_validator(mode="after")
    def clean_title(self):
        self.title = self.title.strip()
        if not self.title:
            raise ValueError("Task title is required")
        return self


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    request_id: str | None = Field(default=None, max_length=120)
    due_date: date | None = None
    priority: TaskPriority | None = None
    completed: bool | None = None

    @model_validator(mode="after")
    def has_change(self):
        if not self.model_fields_set:
            raise ValueError("Provide at least one task change")
        if "title" in self.model_fields_set:
            if self.title is None or not self.title.strip():
                raise ValueError("Task title is required")
            self.title = self.title.strip()
        return self


ACTIVITY_COPY: dict[str, tuple[str, str, str]] = {
    "workspace.created": (
        "review",
        "created a client workspace for",
        "Internal workspace created; client access not yet provisioned",
    ),
    "document.created": (
        "upload",
        "uploaded new evidence for",
        "Evidence received for storage verification",
    ),
    "document.receipt_verified": (
        "upload",
        "completed receipt verification for",
        "File type and storage receipt verified",
    ),
    "request.manual_decision": (
        "review",
        "recorded a human assessment for",
        "Internal auditor decision recorded",
    ),
    "document.feedback": (
        "feedback",
        "sent document-level feedback for",
        "Client feedback contains intake issues only",
    ),
    "request.follow_up": (
        "feedback",
        "requested follow-up evidence for",
        "Additional document requested by the auditor",
    ),
    "questionnaire.answered": (
        "questionnaire",
        "updated a representation for",
        "Response is waiting for human review",
    ),
    "representation.submitted": (
        "questionnaire",
        "submitted a representation for",
        "Response is waiting for human review",
    ),
    "questionnaire.na_approved": (
        "questionnaire",
        "approved a representation for",
        "Human applicability review recorded",
    ),
    "questionnaire.na_rejected": (
        "questionnaire",
        "rejected a representation for",
        "Human applicability review recorded",
    ),
    "engagement.pipeline_stage_changed": (
        "review",
        "moved the workflow stage for",
        "Pipeline coordination only; no report was signed",
    ),
    "auditor_task.completion_changed": (
        "review",
        "updated an internal task for",
        "Task status changed; no finding was finalized",
    ),
    "auditor_task.created": (
        "review",
        "created an internal task for",
        "Internal task created for assigned audit work",
    ),
    "auditor_task.updated": (
        "review",
        "updated an internal task for",
        "Internal task details updated",
    ),
    "report.draft_generated": (
        "review",
        "generated an unsigned draft for",
        "Draft output requires human review and signature",
    ),
}


def readiness(engagement, items=None):
    catalog = load_catalog()
    instances = {item.item_key: item for item in (items if items is not None else engagement.items)}
    blockers = []
    reviewed = 0
    for definition in catalog.requests:
        item = instances.get(definition.id)
        if not item:
            blockers.append(f"{definition.id}: workflow instance missing")
            continue
        if not item.applicability_decision:
            blockers.append(f"{definition.id}: applicability undecided")
        elif item.applicability_decision == "applicable" and not item.assessment:
            blockers.append(f"{definition.id}: assessment undecided")
        else:
            reviewed += 1
        if item.na_review_state == NAReviewState.PENDING:
            blockers.append(f"{definition.id}: client representation awaits review")
        if item.status.value == "checking":
            blockers.append(f"{definition.id}: storage receipt verification pending")
        if item.applicability_decision == "applicable" and item.status.value.startswith(
            "action_needed"
        ):
            blockers.append(f"{definition.id}: replacement or additional document requested")
    return {
        "ready": not blockers,
        "reviewed": reviewed,
        "total": 34,
        "blockers": blockers,
        "meaning": "Ready for human report drafting, not a clean opinion or signed report.",
    }


def _available_firm_slug(db: DB, name: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:80] or "client"
    slug = base
    suffix = 2
    while db.scalar(select(Firm.id).where(Firm.slug == slug)) is not None:
        slug = f"{base}-{suffix}"
        suffix += 1
    return slug


@router.post("/workspaces", status_code=201)
def create_workspace(payload: WorkspaceCreate, user: CurrentUser, db: DB):
    require_auditor(user)
    firm = Firm(name=payload.firm_name, slug=_available_firm_slug(db, payload.firm_name))
    db.add(firm)
    db.flush()
    engagement = Engagement(
        firm_id=firm.id,
        auditor_id=user.id,
        status=EngagementStatus.DRAFT,
        review_period_start=payload.review_period_start,
        review_period_end=payload.review_period_end,
        due_date=payload.due_date,
    )
    db.add(engagement)
    db.flush()
    initialize_engagement(engagement)
    db.add(
        AuditLog(
            firm_id=firm.id,
            actor_id=user.id,
            action="workspace.created",
            entity_type="engagement",
            entity_id=engagement.id,
            details={
                "firm_name": firm.name,
                "checklist_version": engagement.checklist_version,
                "review_period_start": payload.review_period_start.isoformat(),
                "review_period_end": payload.review_period_end.isoformat(),
            },
        )
    )
    db.commit()
    return {
        "id": engagement.id,
        "firmId": firm.id,
        "firmName": firm.name,
        "slug": firm.slug,
        "status": engagement.status,
        "requestCount": len(engagement.items),
        "clientAccessProvisioned": False,
    }


@router.get("/engagements")
def dashboard(user: CurrentUser, db: DB):
    require_auditor(user)
    engagements = db.scalars(
        visible_engagements(user).options(
            selectinload(Engagement.firm), selectinload(Engagement.items)
        )
    ).all()
    return [
        {
            "id": entry.id,
            "firmName": entry.firm.name,
            "firmId": entry.firm_id,
            "status": entry.status,
            "readiness": readiness(entry),
        }
        for entry in engagements
    ]


def _pipeline_next_action(stage: PipelineStage, blocker_count: int) -> str:
    if blocker_count:
        return f"Resolve {blocker_count} outstanding workflow blocker(s)"
    return {
        "intake": "Confirm review period and applicable business lines",
        "document_collection": "Complete document collection and intake review",
        "auditor_review": "Complete the credentialed auditor's human assessment",
        "report_drafting": "Prepare the unsigned draft report for auditor review",
        "awaiting_signature": "Credentialed auditor reviews and explicitly signs the report",
        "complete": "No open action",
    }[stage]


@router.get("/pipeline")
def pipeline(user: CurrentUser, db: DB):
    require_auditor(user)
    engagements = db.scalars(
        visible_engagements(user).options(
            selectinload(Engagement.firm), selectinload(Engagement.auditor)
        )
    ).all()
    result = []
    for engagement in engagements:
        items = db.scalars(
            select(ChecklistItemInstance).where(
                ChecklistItemInstance.engagement_id == engagement.id,
                ChecklistItemInstance.firm_id == engagement.firm_id,
            )
        ).all()
        state = readiness(engagement, items)
        stage = PIPELINE_STATUS_TO_STAGE[engagement.status]
        result.append(
            {
                "id": engagement.id,
                "firm": engagement.firm.name,
                "stage": stage,
                "due": engagement.due_date,
                "assignee": engagement.auditor.name if engagement.auditor else "Unassigned",
                "progress": round(state["reviewed"] / state["total"] * 100),
                "blockers": len(state["blockers"]),
                "nextAction": _pipeline_next_action(stage, len(state["blockers"])),
                "reportSigned": False,
            }
        )
    return result


@router.patch("/engagements/{engagement_id}/pipeline-stage")
def move_pipeline_stage(
    engagement_id: str, payload: PipelineMove, user: CurrentUser, db: DB
):
    require_auditor(user)
    engagement = db.scalar(
        visible_engagements(user).where(Engagement.id == engagement_id)
    )
    if engagement is None:
        raise HTTPException(404, "Engagement not found")
    if payload.stage == "complete":
        raise HTTPException(
            409,
            "Completion requires a separately recorded signed-report action",
        )
    before = PIPELINE_STATUS_TO_STAGE[engagement.status]
    engagement.status = PIPELINE_STAGE_TO_STATUS[payload.stage]
    db.add(
        AuditLog(
            firm_id=engagement.firm_id,
            actor_id=user.id,
            action="engagement.pipeline_stage_changed",
            entity_type="engagement",
            entity_id=engagement.id,
            details={"before": {"stage": before}, "after": {"stage": payload.stage}},
        )
    )
    db.commit()
    return {
        "id": engagement.id,
        "stage": payload.stage,
        "reportSigned": False,
    }


def _visible_task(db: DB, user: CurrentUser, task_id: str) -> AuditorTask:
    task = db.scalar(
        select(AuditorTask)
        .join(
            Engagement,
            (Engagement.id == AuditorTask.engagement_id)
            & (Engagement.firm_id == AuditorTask.firm_id),
        )
        .where(
            AuditorTask.id == task_id,
            AuditorTask.assignee_id == user.id,
            Engagement.auditor_id == user.id,
        )
    )
    if task is None:
        raise HTTPException(404, "Task not found")
    return task


@router.get("/tasks")
def tasks(user: CurrentUser, db: DB):
    require_auditor(user)
    entries = db.scalars(
        select(AuditorTask)
        .join(
            Engagement,
            (Engagement.id == AuditorTask.engagement_id)
            & (Engagement.firm_id == AuditorTask.firm_id),
        )
        .where(
            AuditorTask.assignee_id == user.id,
            Engagement.auditor_id == user.id,
        )
        .options(selectinload(AuditorTask.assignee))
        .order_by(AuditorTask.completed_at, AuditorTask.due_date, AuditorTask.created_at)
    ).all()
    return [
        {
            "id": task.id,
            "engagementId": task.engagement_id,
            "title": task.title,
            "requestId": task.request_id,
            "due": task.due_date,
            "priority": task.priority,
            "assignee": task.assignee.name,
            "completed": task.completed_at is not None,
        }
        for task in entries
    ]


@router.post("/engagements/{engagement_id}/tasks", status_code=201)
def create_task(
    engagement_id: str, payload: TaskCreate, user: CurrentUser, db: DB
):
    require_auditor(user)
    engagement = _get_engagement(db, user, engagement_id)
    task = AuditorTask(
        firm_id=engagement.firm_id,
        engagement_id=engagement.id,
        assignee_id=user.id,
        title=payload.title,
        request_id=payload.request_id,
        due_date=payload.due_date,
        priority=payload.priority,
    )
    db.add(task)
    db.flush()
    db.add(
        AuditLog(
            firm_id=engagement.firm_id,
            actor_id=user.id,
            action="auditor_task.created",
            entity_type="auditor_task",
            entity_id=task.id,
            details={"title": task.title, "request_id": task.request_id},
        )
    )
    db.commit()
    return {
        "id": task.id,
        "engagementId": task.engagement_id,
        "title": task.title,
        "requestId": task.request_id,
        "due": task.due_date,
        "priority": task.priority,
        "assignee": user.name,
        "completed": False,
    }


@router.patch("/tasks/{task_id}")
def update_task(task_id: str, payload: TaskUpdate, user: CurrentUser, db: DB):
    require_auditor(user)
    task = _visible_task(db, user, task_id)
    before = {
        "title": task.title,
        "request_id": task.request_id,
        "due_date": task.due_date.isoformat() if task.due_date else None,
        "priority": task.priority,
        "completed": task.completed_at is not None,
    }
    if "title" in payload.model_fields_set:
        task.title = payload.title or task.title
    if "request_id" in payload.model_fields_set:
        task.request_id = payload.request_id
    if "due_date" in payload.model_fields_set:
        task.due_date = payload.due_date
    if "priority" in payload.model_fields_set and payload.priority is not None:
        task.priority = payload.priority
    if "completed" in payload.model_fields_set and payload.completed is not None:
        task.completed_at = utcnow() if payload.completed else None
        task.completed_by_id = user.id if payload.completed else None
    after = {
        "title": task.title,
        "request_id": task.request_id,
        "due_date": task.due_date.isoformat() if task.due_date else None,
        "priority": task.priority,
        "completed": task.completed_at is not None,
    }
    only_completion = payload.model_fields_set == {"completed"}
    db.add(
        AuditLog(
            firm_id=task.firm_id,
            actor_id=user.id,
            action=(
                "auditor_task.completion_changed" if only_completion else "auditor_task.updated"
            ),
            entity_type="auditor_task",
            entity_id=task.id,
            details={"before": before, "after": after},
        )
    )
    db.commit()
    return {
        "id": task.id,
        "engagementId": task.engagement_id,
        "title": task.title,
        "requestId": task.request_id,
        "due": task.due_date,
        "priority": task.priority,
        "assignee": user.name,
        "completed": task.completed_at is not None,
        "findingFinalized": False,
        "reportSigned": False,
    }


@router.get("/activity")
def activity(user: CurrentUser, db: DB):
    require_auditor(user)
    engagements = db.scalars(
        visible_engagements(user).options(selectinload(Engagement.firm))
    ).all()
    if not engagements:
        return []
    engagement_ids = [engagement.id for engagement in engagements]
    firm_ids = [engagement.firm_id for engagement in engagements]
    context: dict[str, tuple[str, str]] = {
        engagement.id: (engagement.id, engagement.firm.name) for engagement in engagements
    }

    items = db.scalars(
        select(ChecklistItemInstance).where(
            ChecklistItemInstance.engagement_id.in_(engagement_ids),
            ChecklistItemInstance.firm_id.in_(firm_ids),
        )
    ).all()
    for item in items:
        context[item.id] = (item.engagement_id, item.item_key)

    item_ids = [item.id for item in items]
    if item_ids:
        documents = db.scalars(
            select(Document).where(
                Document.item_instance_id.in_(item_ids), Document.firm_id.in_(firm_ids)
            )
        ).all()
        item_context = {item.id: item for item in items}
        for document in documents:
            item = item_context[document.item_instance_id]
            context[document.id] = (item.engagement_id, item.item_key)

    tasks = db.scalars(
        select(AuditorTask).where(
            AuditorTask.engagement_id.in_(engagement_ids),
            AuditorTask.firm_id.in_(firm_ids),
            AuditorTask.assignee_id == user.id,
        )
    ).all()
    for task in tasks:
        context[task.id] = (task.engagement_id, task.request_id or task.title)

    findings = db.scalars(
        select(FindingDraft).where(
            FindingDraft.engagement_id.in_(engagement_ids),
            FindingDraft.firm_id.in_(firm_ids),
        )
    ).all()
    for finding in findings:
        context[finding.id] = (finding.engagement_id, "Finding draft")

    entity_ids = list(context)
    events = db.execute(
        select(AuditLog, User.name)
        .outerjoin(User, User.id == AuditLog.actor_id)
        .where(
            AuditLog.firm_id.in_(firm_ids),
            AuditLog.entity_id.in_(entity_ids),
            AuditLog.action.in_(ACTIVITY_COPY),
        )
        .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        .limit(20)
    ).all()
    result = []
    for event, actor_name in events:
        copy = ACTIVITY_COPY.get(event.action)
        entity = context.get(event.entity_id or "")
        if copy is None or entity is None:
            continue
        engagement_id, subject = entity
        kind, action, safe_context = copy
        result.append(
            {
                "id": event.id,
                "kind": kind,
                "actor": actor_name or "Storage worker",
                "action": action,
                "subject": subject,
                "context": safe_context,
                "occurredAt": event.created_at,
                "engagementId": engagement_id,
            }
        )
    return result


@router.post("/engagements/{engagement_id}/initialize")
def initialize(engagement_id: str, user: CurrentUser, db: DB):
    require_auditor(user)
    engagement = _get_engagement(db, user, engagement_id)
    if engagement.items:
        raise HTTPException(409, "Existing request instances require explicit migration")
    initialize_engagement(engagement)
    db.add(
        AuditLog(
            firm_id=engagement.firm_id,
            actor_id=user.id,
            action="engagement.initialized",
            entity_type="engagement",
            entity_id=engagement.id,
            details={"before": {"requests": 0}, "after": {"requests": 34},
                     "checklist_version": engagement.checklist_version},
        )
    )
    db.commit()
    return {"requests": 34}


@router.get("/engagements/{engagement_id}/workspace")
def workspace(engagement_id: str, user: CurrentUser, db: DB):
    require_auditor(user)
    engagement = _get_engagement(db, user, engagement_id)
    catalog = load_catalog()
    items = db.scalars(
        select(ChecklistItemInstance)
        .where(
            ChecklistItemInstance.engagement_id == engagement.id,
            ChecklistItemInstance.firm_id == engagement.firm_id,
        )
        .options(selectinload(ChecklistItemInstance.documents))
    ).all()
    instances = {item.item_key: item for item in items}
    requests = []
    for definition in catalog.requests:
        item = instances.get(definition.id)
        if item is None:
            continue
        requests.append(
            {
                "id": item.id,
                "requestId": definition.id,
                "title": definition.title,
                "restricted": definition.restricted,
                "stage": definition.stage,
                "applicable": item.applicable,
                "followUp": item.follow_up,
                "naReviewState": item.na_review_state,
                "representation": item.representation,
                "applicability": item.applicability_decision,
                "assessment": item.assessment,
                "notes": item.internal_notes,
                "documents": [
                    {
                        "id": doc.id,
                        "name": doc.original_name,
                        "sha256": doc.sha256,
                        "version": doc.version,
                        "uploadedAt": doc.created_at,
                        "feedbackCode": doc.feedback_code,
                    }
                    for doc in item.documents
                ],
            }
        )
    db.add(
        AuditLog(
            firm_id=engagement.firm_id,
            actor_id=user.id,
            action="engagement.view",
            entity_type="engagement",
            entity_id=engagement.id,
        )
    )
    for item in items:
        for doc in item.documents:
            db.add(
                AuditLog(
                    firm_id=engagement.firm_id,
                    actor_id=user.id,
                    action="document.view",
                    entity_type="document",
                    entity_id=doc.id,
                )
            )
    db.commit()
    entity_ids = [
        engagement.id,
        *[item.id for item in items],
        *[doc.id for item in items for doc in item.documents],
    ]
    entity_ids.extend(
        db.scalars(
            select(FindingDraft.id).where(
                FindingDraft.engagement_id == engagement.id,
                FindingDraft.firm_id == engagement.firm_id,
            )
        )
    )
    events = db.execute(
        select(AuditLog, User.name)
        .outerjoin(User, User.id == AuditLog.actor_id)
        .where(AuditLog.firm_id == engagement.firm_id, AuditLog.entity_id.in_(entity_ids))
        .order_by(AuditLog.created_at, AuditLog.id)
    ).all()
    return {
        "id": engagement.id,
        "firmName": engagement.firm.name,
        "requests": requests,
        "readiness": readiness(engagement),
        "history": [
            {
                "id": event.id,
                "actorId": event.actor_id,
                "actor": name or "Storage worker",
                "action": event.action,
                "entityId": event.entity_id,
                "at": event.created_at,
                "details": event.details,
            }
            for event, name in events
        ],
    }


@router.patch("/engagements/{engagement_id}/items/{item_id}/decision")
def decide(engagement_id: str, item_id: str, payload: ManualDecision, user: CurrentUser, db: DB):
    require_auditor(user)
    engagement, item = intake_item(db, user, engagement_id, item_id)
    before = {
        "applicability": item.applicability_decision,
        "assessment": item.assessment,
        "notes": item.internal_notes,
    }
    item.applicability_decision = payload.applicability
    item.assessment = payload.assessment
    item.internal_notes = payload.notes
    item.applicable = payload.applicability == "applicable"
    if item.na_review_state is not None:
        item.na_review_state = NAReviewState.REJECTED if item.applicable else NAReviewState.APPROVED
        item.na_approved_by_id = user.id
        if item.applicable:
            definition = load_catalog().get(item.item_key)
            item.status = (
                ClientStatus.RESTRICTED_DO_NOT_UPLOAD
                if definition.restricted
                else ClientStatus.WITH_AUDITOR
                if item.documents
                else ClientStatus.REQUESTED
            )
            item.client_reason = "The auditor confirmed that this requested item applies."
    db.add(
        AuditLog(
            firm_id=engagement.firm_id,
            actor_id=user.id,
            action="request.manual_decision",
            entity_type="checklist_item_instance",
            entity_id=item.id,
            details={"before": before, "after": payload.model_dump()},
        )
    )
    db.commit()
    return {"status": "saved", "readiness": readiness(engagement)}
