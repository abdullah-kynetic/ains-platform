"""HTTP API routers."""

from fastapi import APIRouter

from .engagements import router as engagements_router
from .questionnaire import router as questionnaire_router

router = APIRouter()
router.include_router(engagements_router)
router.include_router(questionnaire_router)

__all__ = ["router"]
