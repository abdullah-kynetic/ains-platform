"""Adapter settings. Separate from app.config on purpose. Secrets are SecretStr, never logged."""

from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class AdapterSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=None, extra="ignore")

    ai_enabled: bool = False  # one flag disables every call
    openrouter_api_key: SecretStr = SecretStr("")  # trial key with a spending limit
    ai_service_token: SecretStr = SecretStr("")  # credential the API uses to call this adapter
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    ai_allowlist_path: Path = Path(__file__).with_name("allowlist.json")
    ai_checklist_path: Path = Path("data/checklist/aml_bd_v1.yaml")
    ai_breaker_path: Path = Path("/var/lib/kien-ai/breaker.json")
    ai_max_requests_per_minute: int = Field(default=20, ge=1, le=20)
    # Local daily cap, set to 80% of the free quota (50/day without credit). The key-info
    # endpoint shape is [Verify]; this local counter never depends on it.
    ai_daily_request_cap: int = Field(default=40, ge=1)
    ai_price_cache_seconds: int = 600
    ai_request_timeout_seconds: float = 60
    ai_max_consecutive_errors: int = Field(default=3, ge=1)
    # Daily cap and error counter survive restarts here (SQLite by default; a Postgres URL works).
    ai_state_database_url: str = "sqlite:////var/lib/kien-ai/state.db"
