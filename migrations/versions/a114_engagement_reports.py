"""Persist human-authored reports without changing existing report artifacts."""

import sqlalchemy as sa
from alembic import op

revision = "a114_engagement_reports"
down_revision = "a113_checklist_na"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "engagement_reports",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("firm_id", sa.String(36), sa.ForeignKey("firms.id"), nullable=False),
        sa.Column("engagement_id", sa.String(36), sa.ForeignKey("engagements.id"), nullable=False),
        sa.Column("created_by_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("status", sa.String(12), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("content", sa.JSON(), nullable=False),
        sa.Column("snapshot", sa.JSON(), nullable=False),
        sa.Column("finalized_by_id", sa.String(36), sa.ForeignKey("users.id")),
        sa.Column("finalized_at", sa.DateTime(timezone=True)),
        sa.Column("content_sha256", sa.String(64)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("engagement_id", name="uq_report_engagement"),
        sa.CheckConstraint("status IN ('draft', 'final')", name="ck_report_status"),
    )
    op.create_index("ix_engagement_reports_firm_id", "engagement_reports", ["firm_id"])
    op.create_index("ix_engagement_reports_engagement_id", "engagement_reports", ["engagement_id"])


def downgrade():
    raise RuntimeError("Retain report history during image rollback")
