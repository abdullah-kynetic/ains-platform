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

    document_check_timeout_seconds: int = 300
    report_template: str = "default.json"

    database_url: str = "postgresql+psycopg://ains:ains_dev@localhost:5432/ains"

    # Isolated hosted-Postgres evaluation only. The application never selects this URL
    # automatically; scripts/supabase_poc.py requires an explicit synthetic-only acknowledgement.
    supabase_poc_database_url: SecretStr = SecretStr("")
    supabase_poc_synthetic_only: bool = False

    # Backend-owned sessions. SESSION_SECRET must be set before sign-in can be used.
    session_secret: SecretStr = SecretStr("")
    session_cookie_secure: bool = False
    session_ttl_hours: int = 12
    magic_link_ttl_minutes: int = 15
    auditor_mfa_issuer: str = "AINS"
    auditor_mfa_enrollment_ttl_minutes: int = 10
    client_invitation_ttl_hours: int = 72
    invitation_preview_enabled: bool = False

    # Comma-separated browser origins; wildcard origins are deliberately unsupported.
    cors_origins: str = "http://localhost:3000"

    def parsed_cors_origins(self) -> list[str]:
        return [
            origin.strip().rstrip("/") for origin in self.cors_origins.split(",") if origin.strip()
        ]


@lru_cache
def get_settings() -> Settings:
    return Settings()
