"""Generate explicitly unsigned draft reports from auditor-approved findings."""

from __future__ import annotations

import io
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from html import escape
from pathlib import Path

from docx import Document as DocxDocument
from docx.shared import Inches, Pt
from pydantic import BaseModel
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from app.database.models import Engagement, FindingDraft

TEMPLATE_ROOT = Path(__file__).resolve().parents[2] / "templates" / "report"


class ReportTemplate(BaseModel):
    firm_name: str
    report_title: str
    report_subtitle: str
    confidentiality: str
    draft_notice: str
    findings_heading: str
    no_findings_text: str


@dataclass(frozen=True)
class ReportArtifact:
    data: bytes
    media_type: str
    filename: str


def _load_template(name: str) -> ReportTemplate:
    candidate = (TEMPLATE_ROOT / name).resolve()
    if TEMPLATE_ROOT.resolve() not in candidate.parents or candidate.suffix != ".json":
        raise ValueError("Invalid report template")
    return ReportTemplate.model_validate(json.loads(candidate.read_text(encoding="utf-8")))


def _citation_text(finding: FindingDraft) -> list[str]:
    return [
        f"Page {citation['page']}: {citation['quote']}"
        for citation in finding.citations
        if citation.get("page") and citation.get("quote")
    ]


class ReportGenerator:
    def __init__(self, template_name: str = "default.json") -> None:
        self.template = _load_template(template_name)

    def generate(
        self, *, engagement: Engagement, findings: list[FindingDraft], output_format: str
    ) -> ReportArtifact:
        if output_format == "docx":
            return self._docx(engagement, findings)
        if output_format == "pdf":
            return self._pdf(engagement, findings)
        raise ValueError("Report format must be docx or pdf")

    def _docx(self, engagement: Engagement, findings: list[FindingDraft]) -> ReportArtifact:
        document = DocxDocument()
        section = document.sections[0]
        section.top_margin = Inches(0.7)
        section.bottom_margin = Inches(0.7)
        styles = document.styles
        styles["Normal"].font.name = "Arial"
        styles["Normal"].font.size = Pt(10)

        document.add_heading(self.template.report_title, 0)
        document.add_paragraph(self.template.report_subtitle)
        document.add_paragraph(self.template.confidentiality)
        notice = document.add_paragraph(self.template.draft_notice)
        notice.runs[0].bold = True
        document.add_heading(engagement.firm.name, level=1)
        document.add_paragraph(
            "Review period: "
            f"{engagement.review_period_start.isoformat()} through "
            f"{engagement.review_period_end.isoformat()}"
        )
        document.add_paragraph(f"Generated: {datetime.now(UTC).date().isoformat()}")
        document.add_heading(self.template.findings_heading, level=1)
        if not findings:
            document.add_paragraph(self.template.no_findings_text)
        for number, finding in enumerate(findings, 1):
            document.add_heading(f"{number}. {finding.title}", level=2)
            document.add_paragraph(f"Severity: {finding.severity.title()}")
            document.add_paragraph(finding.body)
            document.add_paragraph("Evidence citations:")
            for citation in _citation_text(finding):
                document.add_paragraph(citation, style="List Bullet")

        buffer = io.BytesIO()
        document.save(buffer)
        return ReportArtifact(
            data=buffer.getvalue(),
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            filename=f"ains-{engagement.id}-draft-report.docx",
        )

    def _pdf(self, engagement: Engagement, findings: list[FindingDraft]) -> ReportArtifact:
        buffer = io.BytesIO()
        styles = getSampleStyleSheet()
        centered = ParagraphStyle("Centered", parent=styles["Title"], alignment=TA_CENTER)
        report = SimpleDocTemplate(
            buffer,
            pagesize=LETTER,
            rightMargin=0.7 * inch,
            leftMargin=0.7 * inch,
            topMargin=0.7 * inch,
            bottomMargin=0.7 * inch,
            title=self.template.report_title,
            author=self.template.firm_name,
        )
        story = [
            Paragraph(escape(self.template.report_title), centered),
            Paragraph(escape(self.template.report_subtitle), styles["Heading2"]),
            Paragraph(escape(self.template.confidentiality), styles["Italic"]),
            Spacer(1, 12),
            Paragraph(f"<b>{escape(self.template.draft_notice)}</b>", styles["BodyText"]),
            Spacer(1, 18),
            Paragraph(escape(engagement.firm.name), styles["Heading1"]),
            Paragraph(
                "Review period: "
                f"{engagement.review_period_start.isoformat()} through "
                f"{engagement.review_period_end.isoformat()}",
                styles["BodyText"],
            ),
            Paragraph(f"Generated: {datetime.now(UTC).date().isoformat()}", styles["BodyText"]),
            Spacer(1, 18),
            Paragraph(escape(self.template.findings_heading), styles["Heading1"]),
        ]
        if not findings:
            story.append(Paragraph(escape(self.template.no_findings_text), styles["BodyText"]))
        for number, finding in enumerate(findings, 1):
            story.extend(
                [
                    Paragraph(f"{number}. {escape(finding.title)}", styles["Heading2"]),
                    Paragraph(
                        f"<b>Severity:</b> {escape(finding.severity.title())}", styles["BodyText"]
                    ),
                    Paragraph(escape(finding.body), styles["BodyText"]),
                    Paragraph("<b>Evidence citations:</b>", styles["BodyText"]),
                ]
            )
            story.extend(
                Paragraph(f"• {escape(citation)}", styles["BodyText"])
                for citation in _citation_text(finding)
            )
            story.append(Spacer(1, 12))
        report.build(story)
        return ReportArtifact(
            data=buffer.getvalue(),
            media_type="application/pdf",
            filename=f"ains-{engagement.id}-draft-report.pdf",
        )
