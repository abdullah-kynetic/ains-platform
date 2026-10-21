"""Freeze a catalog on a draft engagement, without publishing unapproved requests."""

from app.checklist import ClientStatus
from app.database.models import ChecklistItemInstance, Engagement, EngagementStatus

from .catalog import ChecklistCatalog


def initialize_checklist(engagement: Engagement, catalog: ChecklistCatalog) -> None:
    if engagement.items or engagement.checklist_version:
        raise ValueError("Engagement checklist is already initialized")
    if engagement.status != EngagementStatus.DRAFT:
        raise ValueError("Initialize the checklist on a draft engagement")
    engagement.checklist_version = catalog.version
    engagement.checklist_snapshot = catalog.model_dump(mode="json")
    sections = {section.id: section.title for section in catalog.sections}
    for position, request in enumerate(catalog.items):
        engagement.items.append(ChecklistItemInstance(
            firm_id=engagement.firm_id,
            item_key=request.id,
            section_key=request.section,
            section_title=sections[request.section],
            title=request.title,
            description=request.description,
            accepted_extensions=request.accepted_document_types.copy(),
            # Natural-language period rules need auditor interpretation; do not treat
            # any matching date as proof that the requested coverage is complete.
            review_period_rule=None,
            min_pages=request.min_pages,
            requires_signature=request.requires_signature,
            position=position,
            restricted=request.restricted,
            is_conditional=request.applicability == "conditional",
            condition_question=request.condition_question,
            applicable=request.intake_stage == "initial",
            status=(ClientStatus.RESTRICTED_DO_NOT_UPLOAD if request.restricted
                    else ClientStatus.REQUESTED),
        ))
