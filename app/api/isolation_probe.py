"""Demo support for the isolation screen: hand back a real engagement of a firm the caller is not
assigned to, so the 403/404 shown is a genuine cross-firm denial.

Off unless ISOLATION_PROBE_ENABLED is set (synthetic demo data only). When on, it still answers
only auditors, and only with ids of engagements and firms they are NOT assigned to; it exposes no
other field. A real deployment leaves the flag off and the route answers 404.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel
from sqlalchemy import select

from app.api.auditor import DB, CurrentUser, _require_auditor
from app.config import get_settings
from app.database.models import Engagement

router = APIRouter(prefix="/auditor/isolation-probe", tags=["isolation"])


class IsolationProbeView(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    foreign_engagement_id: str
    foreign_firm_id: str


@router.get("", response_model=IsolationProbeView, response_model_by_alias=True)
def isolation_probe(db: DB, user: CurrentUser) -> IsolationProbeView:
    _require_auditor(user)
    if not get_settings().isolation_probe_enabled:
        raise HTTPException(404, "Not found")
    own_firms = set(db.scalars(select(Engagement.firm_id).where(Engagement.auditor_id == user.id)))
    foreign = db.scalars(
        select(Engagement)
        .where(Engagement.firm_id.not_in(own_firms) if own_firms else True)
        .where((Engagement.auditor_id != user.id) | Engagement.auditor_id.is_(None))
        .order_by(Engagement.created_at)
    ).first()
    if foreign is None:
        raise HTTPException(404, "Not found")
    return IsolationProbeView(foreign_engagement_id=foreign.id, foreign_firm_id=foreign.firm_id)
