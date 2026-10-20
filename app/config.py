"""Application settings loaded from environment variables (and a local .env file).

Secrets are typed as SecretStr so they are never shown in reprs or logs.
"""

from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    egnyte_domain: str = ""
    egnyte_api_key: SecretStr = SecretStr("")
    egnyte_username: str = ""
    egnyte_password: SecretStr = SecretStr("")
    egnyte_dev_root: str = "/Shared/AINS-Dev"

    anthropic_api_key: SecretStr = SecretStr("")
    openai_api_key: SecretStr = SecretStr("")

    database_url: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
