"""S-12: telemetry is rebuilt from safe metadata; provider errors never log user content."""

import json
import logging

import pytest

from app.auth.email import notify_report_ready
from app.config import Settings
from app.documents.scanning import ScanError, UploadRejected, screen_upload
from app.monitoring import configure_private_logging, scrub_event


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


@pytest.mark.parametrize("failed", [False, True])
async def test_upload_audit_omits_untrusted_filename_and_scanner_text(failed):
    marker = "synthetic-private-content@example.test"

    class Scanner:
        def scan(self, content):
            if failed:
                raise ScanError(marker)
            return marker

    with pytest.raises(UploadRejected) as rejected:
        await screen_upload(
            Settings(_env_file=None),
            b"synthetic",
            suffix=".txt",
            sha256="a" * 64,
            filename=marker,
            scanner=Scanner(),
        )
    assert marker not in json.dumps(rejected.value.audit)
    assert "filename" not in rejected.value.audit and "signature" not in rejected.value.audit
    assert rejected.value.audit["sha256"] == "a" * 64


def test_server_access_logs_withhold_tokens_queries_and_private_exception_text(monkeypatch, caplog):
    from uvicorn.logging import AccessFormatter

    marker = "synthetic-private-content@example.test"
    configure_private_logging()
    access = logging.getLogger("uvicorn.access")
    error = logging.getLogger("uvicorn.error")
    for logger in (access, error):
        monkeypatch.setattr(logger, "disabled", False)
        monkeypatch.setattr(logger, "propagate", True)
    with caplog.at_level(logging.INFO, logger="uvicorn.access"):
        access.info(
            '%s - "%s %s HTTP/%s" %d',
            "127.0.0.1",
            "GET",
            f"/auth/invitations/{marker}?email={marker}",
            "1.1",
            200,
        )
    with caplog.at_level(logging.ERROR, logger="uvicorn.error"):
        try:
            raise RuntimeError(marker)
        except RuntimeError:
            error.exception("Provider exception: %s", marker)
    assert marker not in caplog.text and "details withheld" in caplog.text
    record = next(row for row in caplog.records if row.name == "uvicorn.access")
    rendered = AccessFormatter("%(request_line)s %(status_code)s", use_colors=False).format(record)
    assert marker not in rendered and "200" in rendered and "GET" in rendered
    assert all(row.exc_info is None for row in caplog.records)
