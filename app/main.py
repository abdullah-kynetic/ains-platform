"""FastAPI entrypoint."""

from fastapi import FastAPI

app = FastAPI(title="AINS Platform", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness check."""
    return {"status": "ok"}
