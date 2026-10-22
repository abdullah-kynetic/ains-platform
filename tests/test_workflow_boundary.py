from pathlib import Path

from app.config import Settings


def test_workflow_repository_has_no_direct_model_provider() -> None:
    for path in Path("app").rglob("*.py"):
        source = path.read_text()
        assert "api.openai.com" not in source
        assert "api.anthropic.com" not in source
        assert "from openai import" not in source
        assert "import anthropic" not in source
    assert "ai_provider" not in Settings.model_fields
    assert "openai_api_key" not in Settings.model_fields
    assert "anthropic_api_key" not in Settings.model_fields
