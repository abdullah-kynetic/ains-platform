"""Resend transactional email. Never log provider bodies or bearer tokens."""

import logging
from datetime import datetime
from urllib.parse import urlencode

import httpx
from fastapi import HTTPException

from app.config import Settings

logger = logging.getLogger(__name__)

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


def notify_report_ready(
    settings: Settings, *, recipients: list[str], firm_name: str, review_period: str
) -> None:
    """Tell client users a signed report is ready. Never raises, never includes findings.

    A finalized sign-off must not fail because mail could not be sent, so an
    unconfigured sender or a provider error is logged (no addresses, no bodies)
    and skipped.
    """
    api_key = settings.resend_api_key.get_secret_value().strip()
    if not api_key or not settings.email_from:
        logger.info("Report-ready email skipped: email delivery is not configured")
        return
    portal = settings.portal_url.rstrip("/")
    text = (
        f"The independent AML test report for {firm_name} ({review_period}) is ready.\n"
        f"Open {portal}\n"
        "This message does not include report contents.\n"
        f"{PRODUCT_NAME} by {BRAND_NAME} — {BRAND_SITE}"
    )
    for recipient in recipients:
        try:
            response = httpx.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "from": settings.email_from,
                    "to": [recipient],
                    "subject": f"Your {PRODUCT_NAME} report is ready",
                    "text": text,
                },
                timeout=10,
            )
            response.raise_for_status()
        except Exception as exc:  # noqa: BLE001 - sign-off must never fail on mail
            logger.warning("Report-ready email was not delivered (%s)", type(exc).__name__)
