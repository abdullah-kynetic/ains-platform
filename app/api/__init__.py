"""HTTP API routers."""

from fastapi import APIRouter

from .audit_log import router as audit_log_router
from .auditor import router as auditor_router
from .client_invoices import router as client_invoices_router
from .client_profiles import router as client_profiles_router
from .downloads import router as downloads_router
from .engagements import router as engagements_router
from .feed import router as feed_router
from .findings import router as findings_router
from .firm import router as firm_router
from .intake import router as intake_router
from .invoices import router as invoices_router
from .manual_review import router as manual_review_router
from .questionnaire import router as questionnaire_router
from .report_draft import router as report_draft_router
from .reports import router as reports_router
from .signoff import router as signoff_router
from .tenant import router as tenant_router
from .testing import router as testing_router
from .workflow import router as workflow_router
from .workpapers import router as workpapers_router

router = APIRouter()
router.include_router(tenant_router)
router.include_router(client_profiles_router)
router.include_router(reports_router)
router.include_router(invoices_router)
router.include_router(audit_log_router)
router.include_router(auditor_router)
router.include_router(firm_router)
router.include_router(engagements_router)
router.include_router(questionnaire_router)
router.include_router(intake_router)
router.include_router(manual_review_router)
router.include_router(workflow_router)
router.include_router(testing_router)
router.include_router(workpapers_router)
router.include_router(findings_router)
router.include_router(report_draft_router)
router.include_router(signoff_router)
router.include_router(feed_router)
router.include_router(client_invoices_router)
router.include_router(downloads_router)

__all__ = ["router"]
