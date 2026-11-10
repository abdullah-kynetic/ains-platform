"""Auditor edits to assembled report-draft sections. Additive and idempotent.

Revision ID: a125_report_section_edits
Revises: a124_findings_responses
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "a125_report_section_edits"
down_revision: str | None = "a124_findings_responses"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if "report_section_edits" in set(inspect(op.get_bind()).get_table_names()):
        return
    op.create_table(
        "report_section_edits",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("firm_id", sa.String(36), sa.ForeignKey("firms.id"), nullable=False),
        sa.Column("engagement_id", sa.String(36), sa.ForeignKey("engagements.id"), nullable=False),
        sa.Column("section_id", sa.String(80), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("edited_by_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("edited_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("engagement_id", "section_id", name="uq_report_section_edit"),
    )
    op.create_index("ix_report_section_edits_firm_id", "report_section_edits", ["firm_id"])
    op.create_index(
        "ix_report_section_edits_engagement_id", "report_section_edits", ["engagement_id"]
    )
    op.create_index(
        "ix_report_section_edits_firm_engagement",
        "report_section_edits",
        ["firm_id", "engagement_id"],
    )


def downgrade() -> None:
    op.drop_table("report_section_edits")
