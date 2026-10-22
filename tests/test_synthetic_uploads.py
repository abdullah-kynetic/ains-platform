import hashlib

from scripts.evaluate_synthetic import SYNTHETIC_ROOT, run_evaluation


async def test_synthetic_upload_validation_is_offline_and_preserves_bytes() -> None:
    results = await run_evaluation()
    assert len(results) == 6 and all(result.passed for result in results)
    clean = next(result for result in results if result.item_id == "clean")
    assert clean.sha256 == hashlib.sha256((SYNTHETIC_ROOT / "clean.txt").read_bytes()).hexdigest()
    wrong_period = next(result for result in results if result.item_id == "wrong-period")
    assert wrong_period.actual_status == "received"
