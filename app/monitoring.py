"""Opt-in error telemetry. Never forward application-supplied text or objects."""

import logging
from typing import Any

import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration

from app.config import Settings


class PrivateServerLogFilter(logging.Filter):
    """Keep operational status while withholding paths, queries and exception text."""

    def filter(self, record: logging.LogRecord) -> bool:
        if record.name == "uvicorn.access":
            args = record.args if isinstance(record.args, tuple) and len(record.args) == 5 else ()
            method = (
                args[1]
                if args
                and isinstance(args[1], str)
                and args[1] in {"GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"}
                else "OTHER"
            )
            version = (
                args[3]
                if args and isinstance(args[3], str) and args[3] in {"1.0", "1.1", "2", "3"}
                else "?"
            )
            status = args[4] if args and type(args[4]) is int else 0
            # Preserve the five-argument shape required by Uvicorn's AccessFormatter.
            record.msg = '%s - "%s %s HTTP/%s" %d'
            record.args = ("[withheld]", method, "[withheld]", version, status)
            record.exc_info = record.exc_text = record.stack_info = None
        elif record.exc_info or record.exc_text or record.stack_info:
            record.msg = "Application error (details withheld)"
            record.args = ()
            record.exc_info = record.exc_text = record.stack_info = None
        return True


_SERVER_LOG_FILTER = PrivateServerLogFilter()


def configure_private_logging() -> None:
    """Install once per logger, independently of whether Sentry is enabled."""
    for name in ("uvicorn.access", "uvicorn.error"):
        logger = logging.getLogger(name)
        if _SERVER_LOG_FILTER not in logger.filters:
            logger.addFilter(_SERVER_LOG_FILTER)


def scrub_event(event: dict[str, Any], hint: dict[str, Any]) -> dict[str, Any]:
    """Rebuild rather than redact: content can occur under arbitrary keys.

    Messages, exception values, locals/source, URLs, headers, cookies, breadcrumbs,
    users, tags, contexts, extra, documents and SAR data are all deliberately omitted.
    Hints (including original exceptions and attachments) are never serialized here.
    """
    hint.pop("attachments", None)
    frames = []
    for exception in event.get("exception", {}).get("values", []):
        for frame in exception.get("stacktrace", {}).get("frames", []):
            frames.append(
                {key: frame[key] for key in ("lineno", "colno") if type(frame.get(key)) is int}
            )
    return {
        "level": "error",
        "exception": {
            "values": [
                {
                    "type": "ApplicationError",
                    "value": "Application error (details withheld)",
                    "stacktrace": {"frames": frames},
                }
            ]
        },
    }


def init_sentry(settings: Settings) -> None:
    """Do not initialize any SDK integrations or transport without an explicit DSN."""
    if not settings.sentry_dsn.get_secret_value().strip():
        return

    def before_send(event: dict[str, Any], hint: dict[str, Any]) -> dict[str, Any]:
        return {**scrub_event(event, hint), "environment": settings.sentry_environment}

    sentry_sdk.init(
        dsn=settings.sentry_dsn.get_secret_value(),
        environment=settings.sentry_environment,
        traces_sample_rate=settings.sentry_traces_sample_rate,
        send_default_pii=False,
        default_integrations=False,
        auto_enabling_integrations=False,
        integrations=[StarletteIntegration(), FastApiIntegration()],
        max_request_body_size="never",
        include_local_variables=False,
        include_source_context=False,
        max_breadcrumbs=0,
        auto_session_tracking=False,
        send_client_reports=False,
        enable_logs=False,
        enable_metrics=False,
        before_send=before_send,
        # Performance payloads contain SQL, URLs and document metadata. Fail closed.
        before_send_transaction=lambda event, hint: None,
        trace_propagation_targets=[],
    )
