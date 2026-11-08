"""Internal HTTP service. Called only by the API over the private network with a service token."""

import hmac

from fastapi import Depends, FastAPI, Header, HTTPException

from ai_adapter.client import AIAdapter
from ai_adapter.guards import GuardViolation
from ai_adapter.schemas import AnalyzeOutput, AnalyzeRequest
from ai_adapter.settings import AdapterSettings


def create_service(settings: AdapterSettings, adapter: AIAdapter | None = None) -> FastAPI:
    app = FastAPI(title="Kien AI adapter", docs_url=None, redoc_url=None, openapi_url=None)
    state = {"adapter": adapter}

    def require_token(authorization: str = Header(default="")) -> None:
        expected = settings.ai_service_token.get_secret_value()
        presented = authorization.removeprefix("Bearer ").strip()
        if not expected or not hmac.compare_digest(presented, expected):
            raise HTTPException(status_code=401, detail="Unauthorized")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/v1/analyze", response_model=AnalyzeOutput, dependencies=[Depends(require_token)])
    def analyze(req: AnalyzeRequest, model: str) -> AnalyzeOutput:
        if state["adapter"] is None:
            state["adapter"] = AIAdapter(settings)
        try:
            return state["adapter"].analyze(req, model)
        except GuardViolation as violation:
            status = 429 if violation.code in {"rate_limited", "daily_quota_reached"} else 403
            raise HTTPException(status_code=status, detail=violation.code) from None

    return app
