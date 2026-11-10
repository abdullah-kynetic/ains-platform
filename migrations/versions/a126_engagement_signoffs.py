"""Independence declaration, reviewer approval and partner signature. Additive and idempotent.

Revision ID: a126_engagement_signoffs
Revises: a125_report_section_edits
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "a126_engagement_signoffs"
down_revision: str | None = "a125_report_section_edits"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TS = sa.DateTime(timezone=True)


def upgrade() -> None:
    if "engagement_signoffs" in set(inspect(op.get_bind()).get_table_names()):
        return
    users = lambda: sa.ForeignKey("users.id")  # noqa: E731
    op.create_table(
        "engagement_signoffs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("firm_id", sa.String(36), sa.ForeignKey("firms.id"), nullable=False),
        sa.Column("engagement_id", sa.String(36), sa.ForeignKey("engagements.id"), nullable=False),
        sa.Column("independence_answers", sa.JSON(), nullable=False),
        sa.Column("conflicts", sa.Text(), nullable=False, server_default=""),
        sa.Column("safeguards", sa.Text(), nullable=False, server_default=""),
        sa.Column("independence_conclusion", sa.String(20), nullable=True),
        sa.Column("declared_by_id", sa.String(36), users(), nullable=True),
        sa.Column("declared_at", TS, nullable=True),
        sa.Column("reviewer_id", sa.String(36), users(), nullable=True),
        sa.Column("reviewer_approved_at", TS, nullable=True),
        sa.Column("reviewer_note", sa.Text(), nullable=False, server_default=""),
        sa.Column("partner_id", sa.String(36), users(), nullable=True),
        sa.Column("partner_signed_at", TS, nullable=True),
        sa.Column("partner_fingerprint", sa.String(64), nullable=True),
        sa.Column("signed_sections", sa.JSON(), nullable=True),
        sa.Column("completed_at", TS, nullable=True),
        sa.Column("updated_at", TS, nullable=False),
        sa.UniqueConstraint("engagement_id", name="uq_signoff_engagement"),
    )
    op.create_index("ix_engagement_signoffs_firm_id", "engagement_signoffs", ["firm_id"])
    op.create_index(
        "ix_engagement_signoffs_engagement_id", "engagement_signoffs", ["engagement_id"]
    )


def downgrade() -> None:
    op.drop_table("engagement_signoffs")
