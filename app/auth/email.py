"""Resend transactional email. Never log provider bodies or bearer tokens."""

from datetime import datetime
from urllib.parse import urlencode

import httpx
from fastapi import HTTPException

from app.config import Settings


class ResendSender:
    def __init__(self, settings: Settings, purpose: str = "magic-link"):
        self.settings = settings
        self.purpose = purpose

    def send(self, *, email: str, token: str, expires_at: datetime) -> None:
        if not self.settings.resend_api_key.get_secret_value() or not self.settings.email_from:
            raise HTTPException(status_code=503, detail="Email delivery is not configured")
        routes = {
            "magic-link": "sign-in",
            "invitation": "accept-invitation",
            "reset": "reset-password",
        }
        url = f"{self.settings.portal_url.rstrip('/')}/{routes[self.purpose]}?" + urlencode(
            {"token": token}
        )
        try:
            response = httpx.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {self.settings.resend_api_key.get_secret_value()}"
                },
                json={
                    "from": self.settings.email_from,
                    "to": [email],
                    "subject": f"AINS {self.purpose}",
                    "text": f"Open {url}\nExpires {expires_at.isoformat()}.",
                },
                timeout=10,
            )
            response.raise_for_status()
        except httpx.HTTPError:
            raise HTTPException(status_code=503, detail="Email delivery unavailable") from None
