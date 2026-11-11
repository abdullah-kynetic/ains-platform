"""Application settings loaded from environment variables (and a local .env file).

Secrets are typed as SecretStr so they are never shown in reprs or logs.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Error monitoring is completely disabled without an explicit DSN.
    sentry_dsn: SecretStr = SecretStr("")
    sentry_environment: str = "production"
    sentry_traces_sample_rate: float = Field(default=0, ge=0, le=1)

    # Optional Egnyte connector (off by default; select STORAGE_BACKEND=egnyte).
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

    storage_backend: Literal["s3", "egnyte"] = "s3"
    aws_region: str = "us-east-1"
    # "r2" targets Cloudflare R2 (S3 API): set S3_ENDPOINT_URL and AWS_REGION=auto.
    s3_provider: Literal["aws", "r2"] = "aws"
    s3_endpoint_url: str = ""
    s3_bucket: str = ""
    s3_sse: Literal["AES256", "aws:kms"] = "AES256"
    s3_kms_key_id: str = ""
    s3_retention_days: int = Field(default=0, ge=0)
    s3_retention_mode: Literal["COMPLIANCE", "GOVERNANCE"] = "GOVERNANCE"
    # How long evidence of a completed engagement is kept before a firm may ask for erasure.
    # Placeholder until the attorney confirms the period (docs/kb/31-retention-export-erasure.md).
    record_retention_days: int = Field(default=2190, ge=0)
    resend_api_key: SecretStr = SecretStr("")
    demo_password: SecretStr = SecretStr("")
    email_from: str = ""
    invite_email_from: str = ""
    # Bare registrable domain. Empty keeps the local single-portal behavior.
    # Production: kiensolutions.com. Firm portals are https://<slug>.<domain>.
    portal_base_domain: str = ""
    # Concrete origin (http://localhost:3000) or a template: https://{slug}.kiensolutions.com.
    portal_url: str = "http://localhost:3000"
    password_reset_ttl_minutes: int = Field(default=15, ge=1, le=60)

    document_check_timeout_seconds: int = 300

    # "production" turns on start-up safety checks (see app.main.enforce_production_safety).
    env: Literal["development", "production"] = "development"

    # Upload malware scanning. "clamav" needs a clamd daemon; scan failure then blocks uploads.
    upload_scan_mode: Literal["off", "clamav"] = "off"
    clamd_host: str = "127.0.0.1"
    clamd_port: int = Field(default=3310, ge=1, le=65535)
    upload_scan_timeout_seconds: float = Field(default=60, gt=0)

    # Failed sign-in lockout (per email and per client address); recovers after the window.
    signin_max_per_email: int = Field(default=5, ge=1)  # per email AND address pair
    signin_max_per_email_total: int = Field(default=50, ge=1)  # softer ceiling across addresses
    signin_max_per_ip: int = Field(default=30, ge=1)
    signin_lockout_minutes: int = Field(default=15, ge=1)

    # In-process protection (0 disables). Per client address per minute; concurrent uploads
    # across the process, sized for the 4 GB VPS (each upload is buffered, up to 100 MB).
    api_rate_limit_per_minute: int = Field(default=300, ge=0)
    upload_max_concurrent: int = Field(default=3, ge=0)
    report_template: str = "default.json"

    database_url: SecretStr = SecretStr("postgresql+psycopg://ains:ains_dev@localhost:5432/ains")

    # Isolated hosted-Postgres evaluation only. The application never selects this URL
    # automatically; scripts/supabase_poc.py requires an explicit synthetic-only acknowledgement.
    supabase_poc_database_url: SecretStr = SecretStr("")
    supabase_poc_synthetic_only: bool = False

    # Backend-owned sessions. SESSION_SECRET must be set before sign-in can be used.
    session_secret: SecretStr = SecretStr("")
    session_cookie_secure: bool = False
    session_ttl_hours: int = 12
    magic_link_ttl_minutes: int = 15
    auditor_mfa_issuer: str = "Kien Solutions"
    auditor_mfa_enrollment_ttl_minutes: int = 10
    client_invitation_ttl_hours: int = 72
    invitation_preview_enabled: bool = False
    # Demo only: lets the isolation screen fetch a real foreign engagement id (synthetic data).
    isolation_probe_enabled: bool = False
    # Comma-separated invitee emails for app.pilot_seed, matched to its firms in order.
    pilot_invitee_emails: str = ""

    # Extra exact browser origins (wildcards are deliberately unsupported). With
    # PORTAL_BASE_DOMAIN set, the apex, www, auditor and https://<known firm slug>.<domain>
    # are also allowed, read from the firms table.
    # Local development default: portal http://localhost:3000, API http://localhost:8000.
    # Production must set public HTTPS origins and must not include localhost.
    cors_origins: str = "http://localhost:3000"

    @field_validator("portal_base_domain")
    @classmethod
    def bare_portal_domain(cls, value: str) -> str:
        cleaned = value.strip().lower().rstrip(".")
        if cleaned and any(char in cleaned for char in "/:?#@ "):
            raise ValueError("PORTAL_BASE_DOMAIN must be a bare hostname")
        return cleaned

    def parsed_cors_origins(self) -> list[str]:
        return [
            origin.strip().rstrip("/") for origin in self.cors_origins.split(",") if origin.strip()
        ]


@lru_cache
def get_settings() -> Settings:
    return Settings()
