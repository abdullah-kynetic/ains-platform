"""The only way audit_engine reaches a model: the authenticated adapter service over HTTP."""

from __future__ import annotations

from typing import Protocol

import httpx

from ai_adapter.schemas import AnalyzeOutput, AnalyzeRequest


class ModelRefused(Exception):
    """The adapter refused or failed. ``code`` is safe to show (no document content)."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


class ModelClient(Protocol):
    def analyze(self, req: AnalyzeRequest, model_id: str) -> AnalyzeOutput: ...


class HttpAdapterClient:
    def __init__(self, base_url: str, token: str, http: httpx.Client | None = None):
        self.base_url = base_url.rstrip("/")
        self._token = token
        self.http = http or httpx.Client(timeout=120)

    def analyze(self, req: AnalyzeRequest, model_id: str) -> AnalyzeOutput:
        try:
            resp = self.http.post(
                f"{self.base_url}/v1/analyze",
                params={"model": model_id},
                json=req.model_dump(),
                headers={"Authorization": f"Bearer {self._token}"},
            )
        except httpx.HTTPError:
            raise ModelRefused("service_unreachable") from None
        if resp.status_code == 200:
            try:
                return AnalyzeOutput.model_validate(resp.json())
            except Exception:  # noqa: BLE001
                raise ModelRefused("bad_output") from None
        if resp.status_code == 401:
            raise ModelRefused("service_unauthorized")
        try:
            code = str(resp.json().get("detail", "refused"))[:60]
        except Exception:  # noqa: BLE001
            code = "refused"
        raise ModelRefused(code)
