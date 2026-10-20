"""Score client-status decisions against the credential-free synthetic evaluation set."""

from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import date
from pathlib import Path
from typing import Literal, Protocol

from pydantic import BaseModel

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.checklist import ClientStatus  # noqa: E402
from app.checks.deterministic import contains_sar_indicator, run_deterministic_checks  # noqa: E402
from app.checks.processor import client_decision  # noqa: E402
from app.checks.providers import LLMDocumentCheck, get_check_provider  # noqa: E402
from app.config import Settings  # noqa: E402
from app.database.models import ChecklistItemInstance, Engagement  # noqa: E402

SYNTHETIC_ROOT = ROOT / "data" / "synthetic"
MANIFEST = SYNTHETIC_ROOT / "manifest.json"


class ReviewPeriod(BaseModel):
    start: date
    end: date


class EvalCase(BaseModel):
    item_id: str
    filename: str | None
    title: str
    description: str
    review_period_rule: str | None
    min_pages: int
    requires_signature: bool
    expected_status: ClientStatus
    expected_ai_called: bool


class EvalManifest(BaseModel):
    review_period: ReviewPeriod
    cases: list[EvalCase]


class EvalResult(BaseModel):
    item_id: str
    expected_status: ClientStatus
    actual_status: ClientStatus
    expected_ai_called: bool
    ai_called: bool

    @property
    def passed(self) -> bool:
        return (
            self.expected_status == self.actual_status
            and self.expected_ai_called == self.ai_called
        )


class EvalProvider(Protocol):
    name: str

    async def check(
        self,
        *,
        item_title: str,
        item_description: str,
        review_period_start: str,
        review_period_end: str,
        pages: list[str],
    ) -> LLMDocumentCheck: ...

    async def aclose(self) -> None: ...


class OfflineBaselineProvider:
    """Credential-free baseline for testing routing around the provider boundary."""

    name = "offline-baseline"

    def __init__(self) -> None:
        self.calls = 0

    async def check(self, **_: object) -> LLMDocumentCheck:
        self.calls += 1
        return LLMDocumentCheck(
            document_usable=True,
            document_type_matches=True,
            review_period_supported=True,
            needs_more_documents=False,
            client_reason_code="none",
        )

    async def aclose(self) -> None:
        return None


def load_manifest(path: Path = MANIFEST) -> EvalManifest:
    return EvalManifest.model_validate_json(path.read_text(encoding="utf-8"))


async def evaluate_case(
    case: EvalCase,
    review_period: ReviewPeriod,
    provider: EvalProvider,
    synthetic_root: Path = SYNTHETIC_ROOT,
) -> EvalResult:
    if case.filename is None:
        return EvalResult(
            item_id=case.item_id,
            expected_status=case.expected_status,
            actual_status=ClientStatus.REQUESTED,
            expected_ai_called=case.expected_ai_called,
            ai_called=False,
        )

    item = ChecklistItemInstance(
        id=f"eval-{case.item_id}",
        firm_id="synthetic-firm",
        engagement_id="synthetic-engagement",
        item_key=case.item_id,
        section_key="synthetic-evaluation",
        section_title="Synthetic evaluation",
        title=case.title,
        description=case.description,
        review_period_rule=case.review_period_rule,
        min_pages=case.min_pages,
        requires_signature=case.requires_signature,
    )
    engagement = Engagement(
        id="synthetic-engagement",
        firm_id="synthetic-firm",
        review_period_start=review_period.start,
        review_period_end=review_period.end,
    )
    content = (synthetic_root / case.filename).read_bytes()
    report = run_deterministic_checks(
        item=item,
        engagement=engagement,
        filename=case.filename,
        content=content,
    )

    ai_called = False
    if contains_sar_indicator(case.filename, report.extracted):
        actual = ClientStatus.WITH_AUDITOR
    elif report.blocking_reason_code:
        actual = (
            ClientStatus.ACTION_NEEDED_MORE
            if report.blocking_reason_code == "missing_pages"
            else ClientStatus.ACTION_NEEDED_REUPLOAD
        )
    elif report.requires_manual_review:
        actual = ClientStatus.WITH_AUDITOR
    else:
        ai_called = True
        provider_result = await provider.check(
            item_title=item.title,
            item_description=item.description,
            review_period_start=review_period.start.isoformat(),
            review_period_end=review_period.end.isoformat(),
            pages=report.extracted.pages,
        )
        actual, _ = client_decision(provider_result)

    return EvalResult(
        item_id=case.item_id,
        expected_status=case.expected_status,
        actual_status=actual,
        expected_ai_called=case.expected_ai_called,
        ai_called=ai_called,
    )


async def run_evaluation(
    provider: EvalProvider,
    manifest: EvalManifest | None = None,
    synthetic_root: Path = SYNTHETIC_ROOT,
) -> list[EvalResult]:
    suite = manifest or load_manifest()
    try:
        return [
            await evaluate_case(case, suite.review_period, provider, synthetic_root)
            for case in suite.cases
        ]
    finally:
        await provider.aclose()


def _provider(name: Literal["offline", "anthropic", "openai"]) -> EvalProvider:
    if name == "offline":
        return OfflineBaselineProvider()
    # Evaluate only process environment variables. Never load a local .env file here.
    settings = Settings(ai_provider=name, _env_file=None)
    return get_check_provider(settings)


async def _main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--provider",
        choices=("offline", "anthropic", "openai"),
        default="offline",
        help="offline is credential-free; live providers receive synthetic files only",
    )
    args = parser.parse_args()
    results = await run_evaluation(_provider(args.provider))
    for result in results:
        mark = "PASS" if result.passed else "FAIL"
        print(
            f"{mark:4} {result.item_id:18} "
            f"status={result.actual_status.value:28} ai_called={str(result.ai_called).lower()}"
        )
    passed = sum(result.passed for result in results)
    print(f"Score: {passed}/{len(results)} ({passed / len(results):.0%})")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main()))
