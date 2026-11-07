"""Separate, authenticated AI adapter (OpenRouter, free models only, synthetic data only).

Nothing under app/ may import this package (tests/test_workflow_boundary.py enforces that).
The workflow works fully without it. Off by default: AI_ENABLED=false.
"""
