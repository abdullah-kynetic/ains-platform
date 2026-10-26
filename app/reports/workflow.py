"""Human report editing built on the catalog, findings and existing report template."""

import hashlib
import json
from html import escape
from html.parser import HTMLParser

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.checklist.catalog import load_catalog
from app.database.models import (
    AuditLog,
    ChecklistItemInstance,
    Engagement,
    EngagementReport,
    FindingDraft,
    ReviewState,
    User,
)
from app.reports import ReportGenerator


class SafeHTML(HTMLParser):
    """Small allowlist: no attributes, URLs, images, SVG, scripts or raw HTML contexts."""

    allowed = {"p", "div", "br", "strong", "b", "em", "i", "ul", "ol", "li", "h2", "h3"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.stack: list[str] = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "iframe", "object", "template"}:
            self.hidden += 1
        elif not self.hidden and tag in self.allowed:
            self.parts.append(f"<{tag}>")
            if tag != "br":
                self.stack.append(tag)

    def handle_endtag(self, tag):
        if tag in {"script", "style", "iframe", "object", "template"}:
            self.hidden = max(0, self.hidden - 1)
        elif not self.hidden and tag in self.stack:
            while self.stack:
                closing = self.stack.pop()
                self.parts.append(f"</{closing}>")
                if closing == tag:
                    break

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(escape(data))


def sanitize(value: str) -> str:
    parser = SafeHTML()
    parser.feed(value)
    parser.close()
    return "".join(parser.parts) + "".join(f"</{tag}>" for tag in reversed(parser.stack))


class SectionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=120)
    html: str = Field(max_length=50000)

    @field_validator("html")
    @classmethod
    def safe_html(cls, value):
        return sanitize(value)


class ReportContent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sections: list[SectionInput] = Field(min_length=1, max_length=10)
    item_findings: dict[str, str] = Field(default_factory=dict, max_length=34)

    @field_validator("item_findings")
    @classmethod
    def valid_findings(cls, findings):
        catalog = load_catalog()
        for key, text in findings.items():
            item = catalog.get(key)
            if not item or len(text) > 5000 or (item.restricted and text.strip()):
                raise ValueError("Use valid request IDs; restricted items permit metadata only")
        return findings


def snapshot(db: Session, engagement: Engagement) -> dict:
    items = db.scalars(
        select(ChecklistItemInstance).where(
            ChecklistItemInstance.engagement_id == engagement.id,
            ChecklistItemInstance.firm_id == engagement.firm_id,
        )
    ).all()
    by_key = {item.item_key: item for item in items}
    return {
        "firmName": engagement.firm.name,
        "period": f"{engagement.review_period_start} – {engagement.review_period_end}",
        "scope": engagement.engagement_type,
        "requests": [
            {
                "requestId": definition.id,
                "title": definition.title,
                "status": (
                    by_key[definition.id].status.value if definition.id in by_key else "requested"
                ),
                "restricted": definition.restricted,
            }
            for definition in load_catalog().requests
        ],
    }


def record(db: Session, report: EngagementReport, user: User, action: str):
    db.add(
        AuditLog(
            firm_id=report.firm_id,
            actor_id=user.id,
            action=f"report.{action}",
            entity_type="engagement",
            entity_id=report.engagement_id,
            details={
                "report_id": report.id,
                "version": report.version,
                "content_sha256": report.content_sha256,
            },
        )
    )


def create_report(db: Session, engagement: Engagement, user: User) -> EngagementReport:
    # Serialize first creation on the existing engagement row.
    db.refresh(engagement, with_for_update=True)
    existing = db.scalar(
        select(EngagementReport).where(
            EngagementReport.engagement_id == engagement.id,
            EngagementReport.firm_id == engagement.firm_id,
        )
    )
    if existing:
        return existing
    template = ReportGenerator().template
    findings = db.scalars(
        select(FindingDraft)
        .where(
            FindingDraft.engagement_id == engagement.id,
            FindingDraft.firm_id == engagement.firm_id,
            FindingDraft.review_state.in_([ReviewState.ACCEPTED, ReviewState.EDITED]),
        )
        .order_by(FindingDraft.created_at)
    ).all()
    report = EngagementReport(
        firm_id=engagement.firm_id,
        engagement_id=engagement.id,
        created_by_id=user.id,
        snapshot=snapshot(db, engagement),
        content=ReportContent(
            sections=[
                SectionInput(title="Scope", html=f"<p>{escape(engagement.engagement_type)}</p>"),
                SectionInput(title="Testing approach", html="<p></p>"),
                SectionInput(
                    title=template.findings_heading,
                    html="".join(
                        f"<h3>{escape(f.title)}</h3><p>{escape(f.body)}</p>" for f in findings
                    )
                    or "<p></p>",
                ),
                SectionInput(title="Conclusion and follow-up", html="<p></p>"),
            ]
        ).model_dump(),
    )
    db.add(report)
    db.flush()
    record(db, report, user, "created")
    return report


def digest(report: EngagementReport) -> str:
    return hashlib.sha256(
        json.dumps(
            {"content": report.content, "snapshot": report.snapshot},
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()


def check_version(report: EngagementReport, version: int):
    if report.version != version:
        raise HTTPException(409, "Report changed. Reload before saving.")
