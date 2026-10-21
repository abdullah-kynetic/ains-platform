"""HTTP API routers."""

from fastapi import APIRouter

from .auditor import router as auditor_router
from .engagements import router as engagements_router
from .onboarding import router as onboarding_router
from .questionnaire import router as questionnaire_router

router = APIRouter()
router.include_router(auditor_router)
router.include_router(engagements_router)
router.include_router(questionnaire_router)
router.include_router(onboarding_router)

__all__ = ["router"]
