"""Synthetic-only privacy regression tests; no telemetry network calls."""

import json
from unittest.mock import patch

import pytest

from app.config import Settings
from app.monitoring import init_sentry, scrub_event


def test_no_dsn_does_not_initialize():
    with patch("app.monitoring.sentry_sdk.init") as init:
        init_sentry(Settings(_env_file=None, sentry_dsn=""))
        init.assert_not_called()


def test_opt_in_is_private():
    with patch("app.monitoring.sentry_sdk.init") as init:
        init_sentry(Settings(_env_file=None, sentry_dsn="https://public@example.invalid/1"))
        options = init.call_args.kwargs
        assert options["send_default_pii"] is False
        assert options["traces_sample_rate"] == 0
        assert options["before_send"]({}, {})["environment"] == "production"
        assert options["max_request_body_size"] == "never"
        assert options["before_send_transaction"]({"spans": ["synthetic"]}, {}) is None


def test_scrubber_removes_all_untrusted_content():
    sensitive = "synthetic@example.invalid synthetic-document-text synthetic-restricted-marker"
    event = dict.fromkeys(
        (
            "request",
            "user",
            "extra",
            "contexts",
            "tags",
            "breadcrumbs",
            "message",
            "logentry",
            "document",
            "sar",
            "unknown_future_field",
        ),
        {"body": sensitive, "cookies": sensitive, "Authorization": sensitive},
    )
    event["exception"] = {
        "values": [
            {
                "type": sensitive,
                "value": sensitive,
                "stacktrace": {
                    "frames": [
                        {
                            "filename": sensitive,
                            "vars": {"document": sensitive},
                            "pre_context": [sensitive],
                            "lineno": 42,
                            "colno": sensitive,
                        }
                    ]
                },
            }
        ]
    }
    hint = {"attachments": [sensitive]}
    clean = scrub_event(event, hint)
    assert sensitive not in json.dumps(clean)
    assert set(clean) == {"level", "exception"}
    assert clean["exception"]["values"][0]["stacktrace"]["frames"] == [{"lineno": 42}]
    assert "attachments" not in hint


def test_sample_rate_range():
    with pytest.raises(ValueError):
        Settings(_env_file=None, sentry_traces_sample_rate=1.1)
