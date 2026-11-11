"""Retention, export and erasure of one client firm's data (readiness item 25).

Three operator actions, run from the command line (there is no HTTP route, so no request can
trigger a deletion):

    uv run python -m app.retention export --firm-id ID [--out FILE]
    uv run python -m app.retention plan   --firm-id ID
    uv run python -m app.retention erase  --firm-id ID --confirm

* **export** writes what the client may already see (their answers, their uploads' metadata and
  hashes, released requests and replies, sent invoices, the signed report without findings) plus
  their own users' names and emails. It never contains findings, workpapers, passwords or hashes.
* **plan** lists which uploaded files could be erased and which are retained, and why.
* **erase** deletes the stored bytes (every object version) of the eligible uploads and replaces
  the receipt with ``erased:<id>``. Rows, hashes and the audit chain stay, so the file's existence
  and fingerprint remain provable. Without ``--confirm`` it only plans.

Rule: evidence of a **completed** engagement is retained for ``RECORD_RETENTION_DAYS`` after
completion. Evidence of an engagement that was never signed is erasable on request. An engagement
that has a partner signature or a final report counts as completed.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from botocore.exceptions import BotoCoreError, ClientError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.database.models import (
    AuditLog,
    ChecklistItemInstance,
    Document,
    Engagement,
    EngagementReport,
    EngagementSignoff,
    EngagementStatus,
    Firm,
    Invoice,
    ResponseRequest,
    User,
    UserRole,
)
from app.storage.s3 import S3Storage

ERASED_PREFIX = "erased:"


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=UTC)


def _iso(value: datetime | None) -> str | None:
    return _aware(value).isoformat() if value else None


def completed_at(db: Session, engagement: Engagement) -> datetime | None:
    """When the engagement counts as completed, or None if it never was."""
    stamps: list[datetime] = []
    signoff = db.scalar(
        select(EngagementSignoff).where(
            EngagementSignoff.engagement_id == engagement.id,
            EngagementSignoff.firm_id == engagement.firm_id,
        )
    )
    if signoff is not None:
        stamps += [t for t in (signoff.partner_signed_at, signoff.completed_at) if t]
    report = db.scalar(
        select(EngagementReport).where(
            EngagementReport.engagement_id == engagement.id,
            EngagementReport.firm_id == engagement.firm_id,
            EngagementReport.status == "final",
        )
    )
    if report is not None and report.finalized_at:
        stamps.append(report.finalized_at)
    if engagement.status == EngagementStatus.COMPLETE and not stamps:
        stamps.append(engagement.updated_at)
    return max(_aware(t) for t in stamps) if stamps else None


@dataclass
class ErasurePlan:
    firm_id: str
    eligible: list[Document] = field(default_factory=list)
    retained: list[tuple[str, str]] = field(default_factory=list)  # (document id, reason)
    skipped: list[tuple[str, str]] = field(default_factory=list)

    def summary(self) -> dict[str, Any]:
        return {
            "firmId": self.firm_id,
            "eligible": len(self.eligible),
            "retained": len(self.retained),
            "skipped": len(self.skipped),
            "retainedReasons": sorted({reason for _, reason in self.retained}),
        }


def plan_erasure(
    db: Session, firm_id: str, settings: Settings, now: datetime | None = None
) -> ErasurePlan:
    now = now or datetime.now(UTC)
    window = timedelta(days=settings.record_retention_days)
    plan = ErasurePlan(firm_id=firm_id)
    done: dict[str, datetime | None] = {}
    documents = db.scalars(
        select(Document).where(Document.firm_id == firm_id).order_by(Document.created_at)
    ).all()
    for document in documents:
        if document.egnyte_path.startswith(ERASED_PREFIX):
            continue
        if not document.egnyte_path.startswith("s3://"):
            plan.skipped.append((document.id, "not on object storage"))
            continue
        if document.engagement_id is None:
            plan.eligible.append(document)
            continue
        if document.engagement_id not in done:
            engagement = db.get(Engagement, document.engagement_id)
            done[document.engagement_id] = (
                completed_at(db, engagement)
                if engagement and engagement.firm_id == firm_id
                else now
            )
        finished = done[document.engagement_id]
        if finished is not None and finished + window > now:
            plan.retained.append(
                (document.id, f"engagement completed; kept until {(finished + window).date()}")
            )
        else:
            plan.eligible.append(document)
    return plan


def erase_firm_files(
    db: Session,
    storage: S3Storage,
    firm_id: str,
    settings: Settings,
    *,
    confirm: bool,
    actor_id: str | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    plan = plan_erasure(db, firm_id, settings, now)
    result = plan.summary() | {"erased": 0, "failed": 0, "confirmed": confirm}
    if not confirm:
        return result
    for document in plan.eligible:
        try:
            storage.delete_receipt(document.egnyte_path)
        except (ValueError, BotoCoreError, ClientError):
            result["failed"] += 1
            continue
        document.egnyte_path = f"{ERASED_PREFIX}{document.id}"
        result["erased"] += 1
    db.add(
        AuditLog(
            firm_id=firm_id,
            actor_id=actor_id,
            action="firm_data.erased",
            entity_type="firm",
            entity_id=firm_id,
            details={k: result[k] for k in ("eligible", "retained", "skipped", "erased", "failed")},
        )
    )
    db.commit()
    return result


def export_firm_data(db: Session, firm_id: str) -> dict[str, Any]:
    firm = db.get(Firm, firm_id)
    if firm is None:
        raise ValueError("Unknown firm")
    out: dict[str, Any] = {
        "firm": {"name": firm.name, "slug": firm.slug},
        "exportedAt": datetime.now(UTC).isoformat(),
        "users": [
            {"name": u.name, "email": u.email, "createdAt": _iso(u.created_at)}
            for u in db.scalars(
                select(User).where(User.firm_id == firm_id, User.role == UserRole.CLIENT)
            )
        ],
        "engagements": [],
        "invoices": [
            {
                "number": f"KIEN-{i.number:04d}",
                "issued": i.issue_date.isoformat(),
                "due": i.due_date.isoformat(),
                "amountCents": i.total_cents,
                "status": i.status,
            }
            for i in db.scalars(
                select(Invoice).where(
                    Invoice.firm_id == firm_id, Invoice.status.in_(["sent", "paid"])
                )
            )
        ],
    }
    for e in db.scalars(select(Engagement).where(Engagement.firm_id == firm_id)):
        signoff = db.scalar(
            select(EngagementSignoff).where(
                EngagementSignoff.engagement_id == e.id, EngagementSignoff.firm_id == firm_id
            )
        )
        signed = signoff is not None and signoff.completed_at is not None
        out["engagements"].append(
            {
                "id": e.id,
                "period": f"{e.review_period_start} to {e.review_period_end}",
                "status": e.status.value,
                "checklist": [
                    {"request": i.item_key, "title": i.title, "status": i.status.value}
                    for i in db.scalars(
                        select(ChecklistItemInstance)
                        .where(
                            ChecklistItemInstance.engagement_id == e.id,
                            ChecklistItemInstance.firm_id == firm_id,
                        )
                        .order_by(ChecklistItemInstance.position)
                    )
                ],
                "documents": [
                    {
                        "number": d.number,
                        "name": d.original_name,
                        "sizeBytes": d.size_bytes,
                        "sha256": d.sha256,
                        "uploadedAt": _iso(d.created_at),
                        "erased": d.egnyte_path.startswith(ERASED_PREFIX),
                    }
                    for d in db.scalars(
                        select(Document)
                        .where(Document.engagement_id == e.id, Document.firm_id == firm_id)
                        .order_by(Document.created_at)
                    )
                ],
                "requestedResponses": [
                    {
                        "title": r.title,
                        "request": r.request_text,
                        "status": r.status,
                        "response": r.response,
                        "respondedAt": _iso(r.responded_at),
                    }
                    for r in db.scalars(
                        select(ResponseRequest).where(
                            ResponseRequest.engagement_id == e.id,
                            ResponseRequest.firm_id == firm_id,
                        )
                    )
                ],
                "signedReport": (
                    {
                        "signedAt": _iso(signoff.partner_signed_at),
                        "fingerprint": signoff.partner_fingerprint,
                        "sections": [
                            {"title": s["title"], "body": s["body"]}
                            for s in signoff.signed_sections or []
                            if not s["id"].startswith("finding-")
                        ],
                    }
                    if signed and signoff
                    else None
                ),
            }
        )
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.retention")
    parser.add_argument("action", choices=["export", "plan", "erase"])
    parser.add_argument("--firm-id", required=True)
    parser.add_argument("--out")
    parser.add_argument("--confirm", action="store_true")
    args = parser.parse_args(argv)
    from app.database.session import get_session_factory

    settings = get_settings()
    with get_session_factory()() as db:
        if args.action == "export":
            text = json.dumps(export_firm_data(db, args.firm_id), indent=2)
            if args.out:
                with open(args.out, "w", encoding="utf-8") as handle:
                    handle.write(text)
            else:
                sys.stdout.write(text + "\n")
            return 0
        storage = S3Storage(settings)
        try:
            result = erase_firm_files(
                db, storage, args.firm_id, settings, confirm=args.confirm and args.action == "erase"
            )
        finally:
            storage.client.close()
        sys.stdout.write(json.dumps(result, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
