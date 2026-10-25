"""Resend transactional email. Never log provider bodies or bearer tokens."""

from datetime import datetime
from urllib.parse import urlencode

import httpx
from fastapi import HTTPException

from app.config import Settings

PRODUCT_NAME = "Kien"
BRAND_NAME = "Kien Solutions"
BRAND_SITE = "https://kiensolutions.com"

_SUBJECTS = {
    "magic-link": f"Sign in to {PRODUCT_NAME}",
    "invitation": f"You're invited to {PRODUCT_NAME}",
    "reset": f"Reset your {PRODUCT_NAME} password",
}


class ResendSender:
    def __init__(self, settings: Settings, purpose: str = "magic-link"):
        self.settings = settings
        self.purpose = purpose

    def send(self, *, email: str, token: str, expires_at: datetime) -> None:
        email_from = self.settings.email_from
        if self.purpose == "invitation" and self.settings.invite_email_from:
            email_from = self.settings.invite_email_from
        if not self.settings.resend_api_key.get_secret_value() or not email_from:
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
                    "from": email_from,
                    "to": [email],
                    "subject": _SUBJECTS[self.purpose],
                    "text": (
                        f"Open {url}\n"
                        f"Expires {expires_at.isoformat()}.\n"
                        f"{PRODUCT_NAME} by {BRAND_NAME} — {BRAND_SITE}"
                    ),
                },
                timeout=10,
            )
            response.raise_for_status()
        except httpx.HTTPError:
            raise HTTPException(status_code=503, detail="Email delivery unavailable") from None
