"""ASGI entry point for the separate AI service: ``uvicorn ai_adapter.main:app``.

Settings come from the process environment only (AI_ENABLED, AI_SERVICE_TOKEN,
OPENROUTER_API_KEY, AI_OWNERSHIP_DATABASE_URL, ...). Nothing is read from a file, and the model
client is built on the first request, so a bad setting fails a call and never the whole process.
With AI_ENABLED unset or false every call is refused; with no AI_SERVICE_TOKEN every call is 401.
"""

from ai_adapter.service import create_service
from ai_adapter.settings import AdapterSettings

app = create_service(AdapterSettings())
