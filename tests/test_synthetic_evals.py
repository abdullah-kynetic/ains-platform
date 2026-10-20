from app.checklist import ClientStatus
from scripts.evaluate_synthetic import OfflineBaselineProvider, load_manifest, run_evaluation


async def test_synthetic_eval_baseline_scores_every_case() -> None:
    provider = OfflineBaselineProvider()
    manifest = load_manifest()
    results = await run_evaluation(provider, manifest)

    assert len(results) == 7
    assert all(result.passed for result in results)
    assert provider.calls == 2

    by_item = {result.item_id: result for result in results}
    assert by_item["planted-sar"].actual_status == ClientStatus.WITH_AUDITOR
    assert by_item["planted-sar"].ai_called is False
    assert by_item["prompt-injection"].actual_status == ClientStatus.ACCEPTED_FOR_TESTING
    assert by_item["prompt-injection"].ai_called is True
