"""S-12: telemetry is rebuilt from safe metadata; provider errors never log user content."""

import json
import logging

from app.auth.email import notify_report_ready
from app.config import Settings
from app.monitoring import scrub_event


def test_unknown_telemetry_fields_and_hint_attachments_cannot_leak_content():
    marker = "synthetic-private-document-and-token@example.test"
    event = {
        key: {"nested": [marker]}
        for key in (
            "message",
            "request",
            "user",
            "extra",
            "tags",
            "breadcrumbs",
            "document",
            "sar",
            "unknown_future_field",
        )
    }
    event["exception"] = {
        "values": [
            {
                "value": marker,
                "stacktrace": {
                    "frames": [
                        {"lineno": 17, "vars": {"private": marker}, "filename": marker},
                    ]
                },
            }
        ]
    }
    hint = {"attachments": [marker]}
    clean = scrub_event(event, hint)
    assert marker not in json.dumps(clean)
    assert set(clean) == {"level", "exception"} and "attachments" not in hint
    assert clean["exception"]["values"][0]["stacktrace"]["frames"] == [{"lineno": 17}]


def test_provider_exception_logs_contain_only_safe_error_metadata(monkeypatch, caplog):
    marker = "synthetic-private-document-and-token@example.test"
    monkeypatch.setattr(logging.getLogger("app.auth.email"), "disabled", False)

    def fail(*args, **kwargs):
        raise RuntimeError(marker)

    monkeypatch.setattr("app.auth.email.httpx.post", fail)
    settings = Settings(
        _env_file=None, resend_api_key="synthetic-only", email_from="sender@example.test"
    )
    notify_report_ready(
        settings,
        recipients=["recipient@example.test"],
        firm_name="Synthetic Firm",
        review_period="2025",
    )
    assert "RuntimeError" in caplog.text
    assert marker not in caplog.text and "recipient@example.test" not in caplog.text
    assert "synthetic-only" not in caplog.text
