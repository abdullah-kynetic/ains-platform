"""Application settings loaded from environment variables (and a local .env file).

Secrets are typed as SecretStr so they are never shown in reprs or logs.
"""

from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Egnyte (Internal app). EGNYTE_API_KEY is the app's Client ID.
    egnyte_domain: str = ""  # subdomain only, e.g. "quintonsfirm"
    egnyte_api_key: SecretStr = SecretStr("")  # Client ID
    egnyte_client_secret: SecretStr = SecretStr("")
    egnyte_username: str = ""
    egnyte_password: SecretStr = SecretStr("")
    egnyte_access_token: SecretStr = SecretStr("")  # optional: skips the password flow
    egnyte_refresh_token: SecretStr = SecretStr("")  # optional: renews expired tokens
    egnyte_scopes: str = "Egnyte.filesystem Egnyte.webhooks"
    egnyte_dev_root: str = "/Shared/AINS-Dev"

    anthropic_api_key: SecretStr = SecretStr("")
    openai_api_key: SecretStr = SecretStr("")

    database_url: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
