"""Resend transactional email.

Production supplies ``RESEND_API_KEY`` from SSM Parameter Store
``/ains-prod/RESEND_API_KEY`` through the process environment. This module only
reads that setting. When the key is blank, delivery is logged and skipped.

Never log provider bodies, recipient addresses, message contents, or bearer tokens.
"""

from __future__ import annotations

import logging
from datetime import datetime
from html import escape
from urllib.parse import urlencode

import httpx
from fastapi import HTTPException

from app.config import Settings

logger = logging.getLogger(__name__)

BRAND_NAME = "Kien Solutions"
EMAIL_FROM = "Kien Solutions <no-reply@kiensolutions.com>"
RESEND_EMAILS_URL = "https://api.resend.com/emails"

_LINK_PURPOSES = {
    "magic-link": ("sign-in", "Sign in to Kien Solutions"),
    "invitation": ("accept-invitation", "You're invited to Kien Solutions"),
    "reset": ("reset-password", "Reset your Kien Solutions password"),
}


class ResendSender:
    def __init__(self, settings: Settings, purpose: str = "magic-link"):
        self.settings = settings
        self.purpose = purpose

    def send(self, *, email: str, token: str, expires_at: datetime) -> None:
        path, subject = _LINK_PURPOSES[self.purpose]
        url = f"{self.settings.portal_url.rstrip('/')}/{path}?" + urlencode({"token": token})
        # Keep "Open {url}" as the first line so existing link parsers stay stable.
        text = f"Open {url}\nExpires {expires_at.isoformat()}.\n\n{BRAND_NAME}"
        html = (
            f"<p><strong>{BRAND_NAME}</strong></p>"
            f'<p><a href="{escape(url, quote=True)}">Open this link</a></p>'
            f"<p>Expires {escape(expires_at.isoformat())}.</p>"
        )
        self._deliver(purpose=self.purpose, email=email, subject=subject, text=text, html=html)

    def send_report_ready(self, *, email: str, firm_name: str, review_period: str) -> None:
        """Tell a client the signed report is available. Never include findings."""
        portal = self.settings.portal_url.rstrip("/")
        text = (
            f"{BRAND_NAME}\n\n"
            f"The independent AML test report for {firm_name} "
            f"({review_period}) is ready.\n"
            f"Open {portal}\n\n"
            "This message does not include report contents."
        )
        html = (
            f"<p><strong>{BRAND_NAME}</strong></p>"
            f"<p>The independent AML test report for {escape(firm_name)} "
            f"({escape(review_period)}) is ready.</p>"
            f'<p><a href="{escape(portal, quote=True)}">Open the portal</a></p>'
            "<p>This message does not include report contents.</p>"
        )
        self._deliver(
            purpose="report-ready",
            email=email,
            subject=f"Your {BRAND_NAME} report is ready",
            text=text,
            html=html,
        )

    def _deliver(self, *, purpose: str, email: str, subject: str, text: str, html: str) -> None:
        api_key = self.settings.resend_api_key.get_secret_value().strip()
        if not api_key:
            logger.info(
                "Transactional email skipped: RESEND_API_KEY is not configured (purpose=%s)",
                purpose,
            )
            return
        try:
            response = httpx.post(
                RESEND_EMAILS_URL,
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "from": EMAIL_FROM,
                    "to": [email],
                    "subject": subject,
                    "text": text,
                    "html": html,
                },
                timeout=10,
            )
        except httpx.HTTPError:
            logger.warning("Transactional email was not delivered (purpose=%s)", purpose)
            raise HTTPException(status_code=503, detail="Email delivery unavailable") from None
        if response.status_code >= 400:
            logger.warning(
                "Transactional email was not delivered (purpose=%s status=%s)",
                purpose,
                response.status_code,
            )
            raise HTTPException(status_code=503, detail="Email delivery unavailable") from None
        logger.info("Transactional email submitted (purpose=%s)", purpose)


def notify_report_ready(
    settings: Settings,
    *,
    recipients: list[str],
    firm_name: str,
    review_period: str,
) -> None:
    """Deliver report-ready mail without failing the auditor's signoff."""
    sender = ResendSender(settings, "report-ready")
    for recipient in recipients:
        try:
            sender.send_report_ready(
                email=recipient, firm_name=firm_name, review_period=review_period
            )
        except HTTPException:
            logger.warning("Transactional report-ready email was not delivered")
