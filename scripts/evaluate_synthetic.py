"""Credential-free synthetic upload validation, with no analysis or network calls."""

from __future__ import annotations

import asyncio
import io
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi import HTTPException, UploadFile  # noqa: E402
from pydantic import BaseModel  # noqa: E402

from app.documents.ingestion import _read_validated, _validated_filename  # noqa: E402

SYNTHETIC_ROOT = ROOT / "data" / "synthetic"


class EvalResult(BaseModel):
    item_id: str
    expected_status: str
    actual_status: str
    sha256: str | None = None

    @property
    def passed(self) -> bool:
        return self.expected_status == self.actual_status


async def run_evaluation() -> list[EvalResult]:
    manifest = json.loads((SYNTHETIC_ROOT / "manifest.json").read_text())
    results = []
    for case in manifest["cases"]:
        status, fingerprint = "missing", None
        if case["filename"]:
            file = UploadFile(filename=case["filename"],
                              file=io.BytesIO((SYNTHETIC_ROOT / case["filename"]).read_bytes()))
            try:
                _, suffix = _validated_filename(file.filename)
                _, fingerprint = await _read_validated(file, suffix)
                status = "received"
            except HTTPException:
                status = "rejected"
            finally:
                await file.close()
        results.append(EvalResult(
            item_id=case["item_id"], expected_status=case["expected_status"],
            actual_status=status, sha256=fingerprint,
        ))
    return results


async def main() -> int:
    results = await run_evaluation()
    for result in results:
        print(f"{'PASS' if result.passed else 'FAIL'} {result.item_id}: {result.actual_status}")
    passed = sum(result.passed for result in results)
    print(f"Upload validation: {passed}/{len(results)}")
    return 0 if all(result.passed for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
