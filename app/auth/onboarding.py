"""Authenticated user's own walkthrough preferences; no caller-controlled identity."""

from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import select

from app.api.engagements import DB, CurrentUser
from app.database.models import AuditLog, User, utcnow

router = APIRouter(prefix="/auth/onboarding", tags=["onboarding"])


class FinishOnboarding(BaseModel):
    action: Literal["completed", "skipped"]


def view(user: User):
    return {"state": user.onboarding_state or "pending", "flow": user.role.value}


@router.get("")
def get(user: CurrentUser):
    return view(user)


@router.post("")
def finish(payload: FinishOnboarding, user: CurrentUser, db: DB):
    # Authentication already loaded this identity. Refresh it after acquiring the
    # lock so another request's committed finish cannot be overwritten by stale state.
    current = db.scalar(
        select(User)
        .where(User.id == user.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if current.onboarding_state is None:
        current.onboarding_state = payload.action
        current.onboarding_finished_at = utcnow()
        db.add(
            AuditLog(
                firm_id=current.firm_id,
                actor_id=current.id,
                action=f"onboarding.{payload.action}",
                entity_type="user",
                entity_id=current.id,
                details={},
            )
        )
        db.commit()
    return view(current)
