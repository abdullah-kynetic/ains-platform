"""S-15: report formatting cannot retain attributes, active URLs or executable elements."""

from html.parser import HTMLParser

import pytest

from app.reports.workflow import SafeHTML, sanitize


class Inspector(HTMLParser):
    def handle_starttag(self, tag, attrs):
        assert tag in SafeHTML.allowed and not attrs


@pytest.mark.parametrize(
    "payload",
    [
        '<p onclick="alert(1)">Synthetic <strong style="color:red">report</strong></p>',
        '<a href="javascript:alert(1)">Synthetic link</a><img src="https://external.example/image">',
        '<script>PRIVATE-SCRIPT-MARKER</script><iframe srcdoc="bad">PRIVATE-FRAME-MARKER</iframe>',
        '<svg onload="alert(1)"><a href="https://external.example">Synthetic</a></svg>',
        "<template><script>PRIVATE-SCRIPT-MARKER</script></template><p>Safe</p>",
    ],
)
def test_only_formatting_survives(payload):
    clean = sanitize(payload)
    Inspector().feed(clean)
    assert "PRIVATE-SCRIPT-MARKER" not in clean and "PRIVATE-FRAME-MARKER" not in clean
    assert "https://external.example" not in clean and "javascript:" not in clean
    assert sanitize(clean) == clean
