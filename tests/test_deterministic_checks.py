import io
from datetime import date

from PIL import Image

from app.checks.deterministic import contains_sar_indicator, run_deterministic_checks
from app.database.models import ChecklistItemInstance, Engagement


def records(**item_values) -> tuple[ChecklistItemInstance, Engagement]:
    values = dict(
        id="item-synthetic",
        firm_id="firm-synthetic",
        engagement_id="engagement-synthetic",
        item_key="approval",
        section_key="governance",
        section_title="Governance",
        title="Signed annual approval",
        min_pages=1,
        review_period_rule="date within engagement review period",
        requires_signature=True,
    )
    values.update(item_values)
    item = ChecklistItemInstance(**values)
    engagement = Engagement(
        id="engagement-synthetic",
        firm_id="firm-synthetic",
        review_period_start=date(2025, 1, 1),
        review_period_end=date(2025, 12, 31),
    )
    return item, engagement


def test_deterministic_text_checks_date_pages_and_signature() -> None:
    item, engagement = records()
    report = run_deterministic_checks(
        item=item,
        engagement=engagement,
        filename="synthetic.txt",
        content=b"Approved 2025-06-30\nElectronically signed by Synthetic Officer",
    )
    assert report.blocking_reason_code is None
    assert [check.status for check in report.checks] == ["passed"] * 4
    assert not report.requires_manual_review


def test_deterministic_wrong_period_has_plain_client_reason() -> None:
    item, engagement = records(requires_signature=False)
    report = run_deterministic_checks(
        item=item,
        engagement=engagement,
        filename="synthetic.txt",
        content=b"Approved 2024-06-30",
    )
    assert report.blocking_reason_code == "wrong_period"
    assert report.checks[-1].client_reason == (
        "The file does not show a date within the requested review period."
    )


def test_valid_image_is_routed_to_manual_review_without_ai_text() -> None:
    item, engagement = records(review_period_rule=None, requires_signature=False)
    buffer = io.BytesIO()
    Image.new("RGB", (20, 20), color="white").save(buffer, format="PNG")
    report = run_deterministic_checks(
        item=item,
        engagement=engagement,
        filename="synthetic.png",
        content=buffer.getvalue(),
    )
    assert report.blocking_reason_code is None
    assert report.requires_manual_review


def test_invalid_pdf_is_rejected_as_unreadable() -> None:
    item, engagement = records()
    report = run_deterministic_checks(
        item=item,
        engagement=engagement,
        filename="synthetic.pdf",
        content=b"not actually a pdf",
    )
    assert report.blocking_reason_code == "unreadable"


def test_sar_indicators_are_detected_in_name_or_text() -> None:
    item, engagement = records(review_period_rule=None, requires_signature=False)
    report = run_deterministic_checks(
        item=item,
        engagement=engagement,
        filename="synthetic.txt",
        content=b"Synthetic SAR narrative for test purposes only",
    )
    assert contains_sar_indicator("synthetic.txt", report.extracted)
    assert contains_sar_indicator("FinCEN-Form-111.txt", report.extracted)
