"""Assemble the engagement report draft from stored human entries, and render it.

Nothing here concludes anything: counts come from the auditor's own checklist conclusions,
finding sections copy the auditor's finding fields, and sample counts come from recorded results.
Draft findings are never included. The output is explicitly an unsigned draft.
"""

from __future__ import annotations

import io
from dataclasses import dataclass
from datetime import date
from xml.sax.saxutils import escape

from docx import Document as DocxDocument
from docx.shared import Pt
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.checklist.catalog import load_catalog
from app.database.models import (
    ChecklistItemInstance,
    Engagement,
    Finding,
    Practice,
    ReportSectionEdit,
    SampleItem,
    SampleSet,
    User,
)

DRAFT_NOTICE = "Draft. Not signed. This is not the final report."


@dataclass(frozen=True)
class Section:
    id: str
    title: str
    body: str


def _day(value: date) -> str:
    return f"{value:%B} {value.day}, {value.year}"


def assembled_sections(db: Session, engagement: Engagement, user: User) -> list[Section]:
    """The sections as generated, before any auditor edit."""
    practice = db.get(Practice, user.practice_id) if user.practice_id else None
    author = practice.name if practice else "The audit firm"
    items = db.scalars(
        select(ChecklistItemInstance).where(
            ChecklistItemInstance.engagement_id == engagement.id,
            ChecklistItemInstance.firm_id == engagement.firm_id,
        )
    ).all()
    known = {request.id for request in load_catalog().requests}
    items = [item for item in items if item.item_key in known]
    count = {
        c: sum(1 for i in items if i.conclusion == c) for c in ("pass", "partial", "fail", "na")
    }
    open_count = sum(1 for i in items if i.conclusion is None)
    tested = len(items) - count["na"]
    sets = db.scalars(
        select(SampleSet).where(
            SampleSet.engagement_id == engagement.id, SampleSet.firm_id == engagement.firm_id
        )
    ).all()
    exceptions = 0
    if sets:
        exceptions = sum(
            1
            for item in db.scalars(
                select(SampleItem).where(
                    SampleItem.set_id.in_([s.id for s in sets]),
                    SampleItem.firm_id == engagement.firm_id,
                )
            )
            if item.result == "exception"
        )
    findings = db.scalars(
        select(Finding)
        .where(
            Finding.engagement_id == engagement.id,
            Finding.firm_id == engagement.firm_id,
            Finding.status != "draft",
        )
        .order_by(Finding.created_at, Finding.id)
    ).all()
    period = f"{_day(engagement.review_period_start)} to {_day(engagement.review_period_end)}"
    plural = "" if exceptions == 1 else "s"
    sections = [
        Section(
            "scope",
            "Scope and objective",
            f"{author} performed an independent test of {engagement.firm.name}’s "
            f"anti-money-laundering program for {period}, as required by FINRA Rule 3310(c).",
        ),
        Section(
            "approach",
            "Approach",
            f"{tested} of {len(items)} requests were tested ({count['na']} marked does not apply). "
            f"Sample testing covered {len(sets)} populations with {exceptions} "
            f"exception{plural} noted.",
        ),
        Section(
            "results",
            "Summary of results",
            f"Pass: {count['pass']}. Partial: {count['partial']}. Fail: {count['fail']}. "
            f"Does not apply: {count['na']}. Not yet concluded: {open_count}.",
        ),
    ]
    for number, finding in enumerate(findings, start=1):
        sections.append(
            Section(
                f"finding-{finding.id}",
                f"Finding {number}: {finding.title}",
                f"Rule: {finding.rule}\nCondition: {finding.condition}\nCause: {finding.cause}\n"
                f"Effect: {finding.effect}\nRecommendation: {finding.recommendation}\n"
                f"Severity: {finding.severity}\n"
                f"Management response: {finding.management_response or 'Not yet received.'}",
            )
        )
    sections.append(
        Section(
            "limitations",
            "Limitations",
            "This report is based on documents provided by the firm. It is not a guarantee that "
            "no violations exist. It is a draft until signed by the credentialed auditor.",
        )
    )
    return sections


def draft_sections(db: Session, engagement: Engagement, user: User) -> list[Section]:
    edits = {
        row.section_id: row.body
        for row in db.scalars(
            select(ReportSectionEdit).where(
                ReportSectionEdit.engagement_id == engagement.id,
                ReportSectionEdit.firm_id == engagement.firm_id,
            )
        )
    }
    return [
        Section(s.id, s.title, edits.get(s.id, s.body))
        for s in assembled_sections(db, engagement, user)
    ]


def render_docx(title: str, sections: list[Section]) -> bytes:
    document = DocxDocument()
    document.styles["Normal"].font.name = "Arial"
    document.styles["Normal"].font.size = Pt(10)
    document.add_heading(title, 0)
    document.add_paragraph(DRAFT_NOTICE)
    for section in sections:
        document.add_heading(section.title, 1)
        for line in section.body.split("\n"):
            document.add_paragraph(line)
    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def render_pdf(title: str, sections: list[Section]) -> bytes:
    styles = getSampleStyleSheet()
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=LETTER, title=title)
    story = [
        Paragraph(escape(title), styles["Title"]),
        Paragraph(escape(DRAFT_NOTICE), styles["Italic"]),
    ]
    for section in sections:
        story += [Spacer(1, 10), Paragraph(escape(section.title), styles["Heading2"])]
        story += [
            Paragraph(escape(line) or "&nbsp;", styles["BodyText"])
            for line in section.body.split("\n")
        ]
    doc.build(story)
    return buffer.getvalue()
