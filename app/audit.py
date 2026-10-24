"""Append-only, per-firm SHA-256 audit chains. No document contents are recorded here."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from datetime import UTC
from typing import TypedDict

from sqlalchemy import event, select, text
from sqlalchemy.orm import ORMExecuteState, Session

from app.database.models import AuditLog, new_id, utcnow

GENESIS = "0" * 64


def digest(row: AuditLog) -> str:
    at = row.created_at.replace(tzinfo=UTC) if row.created_at.tzinfo is None else row.created_at
    payload = [
        row.id,
        row.firm_id,
        row.actor_id,
        row.action,
        row.entity_type,
        row.entity_id,
        row.details,
        at.astimezone(UTC).isoformat(),
        row.ip_address,
        row.sequence,
        row.previous_hash,
    ]
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()


class Verification(TypedDict):
    valid: bool
    checked: int
    broken_at: str | None


def verify(rows: Sequence[AuditLog]) -> Verification:
    previous = GENESIS
    for position, row in enumerate(rows, 1):
        if row.sequence != position or row.previous_hash != previous or row.row_hash != digest(row):
            return {"valid": False, "checked": position, "broken_at": row.id}
        previous = row.row_hash
    return {"valid": True, "checked": len(rows), "broken_at": None}


@event.listens_for(Session, "before_flush")
def append_chains(session: Session, context: object, instances: object) -> None:
    for row in session.deleted:
        if isinstance(row, AuditLog):
            raise ValueError("Audit log is append-only")
    for row in session.dirty:
        if isinstance(row, AuditLog) and session.is_modified(row, include_collections=True):
            raise ValueError("Audit log is append-only")
    pending = [row for row in session.new if isinstance(row, AuditLog)]
    if not pending:
        return
    if session.bind.dialect.name == "postgresql":
        session.execute(text("SELECT pg_advisory_xact_lock(3310109)"))
    heads: dict[str | None, AuditLog | None] = {}
    for row in pending:
        if row.firm_id not in heads:
            heads[row.firm_id] = session.scalar(
                select(AuditLog)
                .where(AuditLog.firm_id == row.firm_id)
                .order_by(AuditLog.sequence.desc())
                .limit(1)
            )
        head = heads[row.firm_id]
        row.id = row.id or new_id()
        row.created_at = row.created_at or utcnow()
        row.details = row.details or {}
        row.ip_address = row.ip_address or session.info.get("ip_address")
        row.sequence = head.sequence + 1 if head else 1
        row.previous_hash = head.row_hash if head else GENESIS
        row.row_hash = digest(row)
        heads[row.firm_id] = row


@event.listens_for(Session, "do_orm_execute")
def prevent_bulk_mutation(state: ORMExecuteState) -> None:
    if (state.is_update or state.is_delete) and state.statement.table.name == "audit_logs":
        raise ValueError("Audit log is append-only")
