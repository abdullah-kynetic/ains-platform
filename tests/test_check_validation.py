import pytest

from app.checklist import ClientStatus
from app.checks.processor import client_decision
from app.checks.providers import (
    Citation,
    FindingCandidate,
    LLMDocumentCheck,
    ProviderError,
    validate_citations,
)


def result(**updates) -> LLMDocumentCheck:
    values = dict(
        document_usable=True,
        document_type_matches=True,
        review_period_supported=True,
        needs_more_documents=False,
        client_reason_code="none",
    )
    values.update(updates)
    return LLMDocumentCheck(**values)


def cited(page: int, quote: str) -> LLMDocumentCheck:
    return result(findings=[FindingCandidate(
        title="Synthetic finding", body="Requires auditor review", severity="low",
        citations=[Citation(page=page, quote=quote)],
    )])


def test_wrong_review_period_cannot_be_accepted() -> None:
    status, reason = client_decision(result(review_period_supported=False))
    assert status == ClientStatus.ACTION_NEEDED_REUPLOAD
    assert "review period" in reason


def test_uncertain_period_requires_auditor() -> None:
    assert client_decision(result(review_period_supported=None)) == (
        ClientStatus.WITH_AUDITOR, None,
    )


@pytest.mark.parametrize("page,quote", [(2, "Evidence"), (1, "Invented evidence"), (1, " ")])
def test_fabricated_citation_is_rejected(page: int, quote: str) -> None:
    with pytest.raises(ProviderError):
        validate_citations(cited(page, quote), ["Evidence from a synthetic document"])


def test_exact_citation_allows_layout_whitespace() -> None:
    validate_citations(cited(1, "Evidence from a synthetic document"), [
        "Evidence from\n a synthetic document",
    ])


def test_openai_schema_forbids_extra_fields_in_all_objects() -> None:
    schema = LLMDocumentCheck.model_json_schema()
    assert schema["additionalProperties"] is False
    assert all(
        definition["additionalProperties"] is False
        for definition in schema["$defs"].values()
    )
