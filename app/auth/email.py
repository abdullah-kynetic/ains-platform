"""Resend transactional email. Never log provider bodies or bearer tokens."""

from datetime import UTC, datetime
from urllib.parse import urlencode

import httpx
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.database.models import Firm, User, UserRole
from app.tenancy import portal_url_for

_TOKEN_ROUTES = {
    "magic-link": "sign-in",
    "invitation": "accept-invitation",
    "reset": "reset-password",
}


class ResendSender:
    def __init__(self, settings: Settings, purpose: str = "magic-link"):
        self.settings = settings
        self.purpose = purpose

    def send(
        self, *, email: str, token: str, expires_at: datetime, slug: str | None = None
    ) -> None:
        if not self.settings.resend_api_key.get_secret_value() or not self.settings.email_from:
            raise HTTPException(status_code=503, detail="Email delivery is not configured")
        try:
            base = portal_url_for(self.settings, slug)
        except ValueError:
            raise HTTPException(status_code=503, detail="Firm portal link is unavailable") from None
        if self.purpose == "report-ready":
            # Portal home only. No findings, digest, or report contents.
            subject = "AINS report-ready"
            text = f"A report is ready in your firm portal.\n{base}/\n"
        else:
            url = f"{base}/{_TOKEN_ROUTES[self.purpose]}?" + urlencode({"token": token})
            subject = f"AINS {self.purpose}"
            text = f"Open {url}\nExpires {expires_at.isoformat()}."
        try:
            response = httpx.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {self.settings.resend_api_key.get_secret_value()}"
                },
                json={
                    "from": self.settings.email_from,
                    "to": [email],
                    "subject": subject,
                    "text": text,
                },
                timeout=10,
            )
            response.raise_for_status()
        except httpx.HTTPError:
            raise HTTPException(status_code=503, detail="Email delivery unavailable") from None


def send_report_ready_notices(settings: Settings, db: Session, *, firm_id: str) -> None:
    """Tell that firm's active clients a report is ready. Other firms are not mailed.

    Sign-off still succeeds when email is unconfigured or the provider errors.
    The message has no findings and no report digest.
    """
    if not settings.resend_api_key.get_secret_value() or not settings.email_from:
        return
    firm = db.get(Firm, firm_id)
    if firm is None:
        return
    addresses = db.scalars(
        select(User.email).where(
            User.firm_id == firm.id,
            User.role == UserRole.CLIENT,
            User.is_active.is_(True),
        )
    ).all()
    sender = ResendSender(settings, "report-ready")
    for address in addresses:
        try:
            sender.send(email=address, token="", expires_at=datetime.now(UTC), slug=firm.slug)
        except HTTPException:
            return
