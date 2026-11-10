"""Public firm branding for the portal host. No session and no other firm fields."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.database.models import Firm
from app.database.session import get_db
from app.tenancy import resolve_portal

router = APIRouter(prefix="/tenant", tags=["tenant"])


class TenantBranding(BaseModel):
    """The only fields a portal may show before sign-in."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    name: str
    logo_url: str | None = None


@router.get("/branding", response_model=TenantBranding, response_model_by_alias=True)
def tenant_branding(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> TenantBranding:
    decision = resolve_portal(request, settings)
    if decision.kind != "firm" or not decision.slug:
        raise HTTPException(status_code=404, detail="Unknown firm portal")
    firm = db.scalar(select(Firm).where(Firm.slug == decision.slug))
    if firm is None:
        raise HTTPException(status_code=404, detail="Unknown firm portal")
    return TenantBranding(name=firm.name, logo_url=firm.logo_url)
