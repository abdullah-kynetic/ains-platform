"""AI analysis runs and drafts (Stage 3). Additive, idempotent.

Revision ID: a130_ai_analysis
Revises: a129_email_sign_in_codes
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "a130_ai_analysis"
down_revision: str | None = "a129_email_sign_in_codes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    tables = set(inspect(op.get_bind()).get_table_names())
    if "ai_runs" not in tables:
        op.create_table(
            "ai_runs",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("firm_id", sa.String(36), sa.ForeignKey("firms.id"), nullable=False),
            sa.Column(
                "engagement_id", sa.String(36), sa.ForeignKey("engagements.id"), nullable=False
            ),
            sa.Column("started_by_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("models", sa.JSON(), nullable=False),
            sa.Column("documents_analyzed", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("skipped", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_ai_runs_firm_id", "ai_runs", ["firm_id"])
        op.create_index("ix_ai_runs_engagement_id", "ai_runs", ["engagement_id"])
        op.create_index("ix_ai_runs_firm_engagement", "ai_runs", ["firm_id", "engagement_id"])
    if "ai_drafts" not in tables:
        op.create_table(
            "ai_drafts",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("firm_id", sa.String(36), sa.ForeignKey("firms.id"), nullable=False),
            sa.Column(
                "engagement_id", sa.String(36), sa.ForeignKey("engagements.id"), nullable=False
            ),
            sa.Column("run_id", sa.String(36), sa.ForeignKey("ai_runs.id"), nullable=False),
            sa.Column("kind", sa.String(20), nullable=False),
            sa.Column("item_key", sa.String(120), nullable=False),
            sa.Column("document_id", sa.String(36), sa.ForeignKey("documents.id"), nullable=False),
            sa.Column("page", sa.Integer(), nullable=False),
            sa.Column("title", sa.String(255), nullable=False),
            sa.Column("body", sa.Text(), nullable=False),
            sa.Column("model", sa.String(120), nullable=False),
            sa.Column("status", sa.String(10), nullable=False, server_default="pending"),
            sa.Column("edited", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("finding_id", sa.String(36), sa.ForeignKey("findings.id")),
            sa.Column("decided_by_id", sa.String(36), sa.ForeignKey("users.id")),
            sa.Column("decided_at", sa.DateTime(timezone=True)),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.CheckConstraint(
                "status in ('pending','accepted','rejected')", name="ck_ai_draft_status"
            ),
            sa.CheckConstraint(
                "kind in ('finding','document_flag','client_request')", name="ck_ai_draft_kind"
            ),
        )
        op.create_index("ix_ai_drafts_firm_id", "ai_drafts", ["firm_id"])
        op.create_index("ix_ai_drafts_engagement_id", "ai_drafts", ["engagement_id"])
        op.create_index("ix_ai_drafts_run_id", "ai_drafts", ["run_id"])
        op.create_index("ix_ai_drafts_firm_engagement", "ai_drafts", ["firm_id", "engagement_id"])


def downgrade() -> None:
    op.drop_table("ai_drafts")
    op.drop_table("ai_runs")
