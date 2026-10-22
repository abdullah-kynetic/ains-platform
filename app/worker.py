"""Durable async document-check worker.

Run once with ``uv run python -m app.worker --once`` or continuously without ``--once``.
"""

from __future__ import annotations

import argparse
import asyncio
from datetime import UTC, datetime, timedelta
from typing import Protocol

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.checks.processor import DocumentProcessor
from app.config import Settings, get_settings
from app.database.models import CheckJob, CheckJobStatus
from app.database.session import get_session_factory

MAX_JOB_ATTEMPTS = 3


class Processor(Protocol):
    async def process(self, db: Session, document_id: str) -> int: ...


def _claim_job(db: Session, settings: Settings) -> CheckJob | None:
    now = datetime.now(UTC)
    stale_before = now - timedelta(seconds=settings.document_check_timeout_seconds * 2)
    db.execute(
        update(CheckJob)
        .where(CheckJob.status == CheckJobStatus.RUNNING, CheckJob.started_at < stale_before)
        .values(
            status=CheckJobStatus.QUEUED,
            available_at=now,
            last_error_code="stale_job_recovered",
        )
    )
    job = db.scalar(
        select(CheckJob)
        .where(
            CheckJob.status == CheckJobStatus.QUEUED,
            CheckJob.available_at <= now,
        )
        .order_by(CheckJob.created_at)
        .with_for_update(skip_locked=True)
        .limit(1)
    )
    if not job:
        db.commit()
        return None
    job.status = CheckJobStatus.RUNNING
    job.started_at = now
    job.attempts += 1
    db.commit()
    return job


async def run_once(
    db: Session,
    settings: Settings,
    *,
    processor: Processor | None = None,
) -> bool:
    job = _claim_job(db, settings)
    if not job:
        return False
    processor = processor or DocumentProcessor(settings)
    try:
        async with asyncio.timeout(settings.document_check_timeout_seconds):
            duration_ms = await processor.process(db, job.document_id)
    except Exception as error:
        db.rollback()
        job = db.get(CheckJob, job.id)
        if not job:
            raise
        job.last_error_code = type(error).__name__[:120]
        if job.attempts < MAX_JOB_ATTEMPTS:
            job.status = CheckJobStatus.QUEUED
            job.available_at = datetime.now(UTC) + timedelta(seconds=2**job.attempts)
        else:
            job.status = CheckJobStatus.FAILED
            job.completed_at = datetime.now(UTC)
        db.commit()
        return True

    job.status = CheckJobStatus.SUCCEEDED
    job.completed_at = datetime.now(UTC)
    job.duration_ms = duration_ms
    job.last_error_code = None
    db.commit()
    return True


async def run(poll_seconds: float, once: bool) -> None:
    settings = get_settings()
    factory = get_session_factory()
    while True:
        with factory() as db:
            processed = await run_once(db, settings)
        if once or not processed:
            if once:
                return
            await asyncio.sleep(poll_seconds)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true", help="Process at most one queued job")
    parser.add_argument("--poll-seconds", type=float, default=2.0)
    args = parser.parse_args()
    asyncio.run(run(max(args.poll_seconds, 0.1), args.once))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
