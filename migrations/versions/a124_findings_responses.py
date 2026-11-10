"""Findings and finding-based client response requests. Additive and idempotent.

Revision ID: a124_findings_responses
Revises: a123_workpapers_samples
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "a124_findings_responses"
down_revision: str | None = "a123_workpapers_samples"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TS = sa.DateTime(timezone=True)


def upgrade() -> None:
    tables = set(inspect(op.get_bind()).get_table_names())
    if "findings" not in tables:
        op.create_table(
            "findings",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("firm_id", sa.String(36), sa.ForeignKey("firms.id"), nullable=False),
            sa.Column(
                "engagement_id", sa.String(36), sa.ForeignKey("engagements.id"), nullable=False
            ),
            sa.Column("title", sa.String(255), nullable=False),
            sa.Column("rule", sa.Text(), nullable=False),
            sa.Column("condition", sa.Text(), nullable=False),
            sa.Column("cause", sa.Text(), nullable=False),
            sa.Column("effect", sa.Text(), nullable=False),
            sa.Column("recommendation", sa.Text(), nullable=False),
            sa.Column("severity", sa.String(10), nullable=False),
            sa.Column("citations", sa.JSON(), nullable=False),
            sa.Column("status", sa.String(10), nullable=False),
            sa.Column("management_response", sa.Text(), nullable=False),
            sa.Column("responded_at", TS, nullable=True),
            sa.Column("created_by_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("created_at", TS, nullable=False),
            sa.Column("updated_at", TS, nullable=False),
            sa.CheckConstraint(
                "status in ('draft','approved','issued','responded','closed')",
                name="ck_finding_status",
            ),
            sa.CheckConstraint(
                "severity in ('low','moderate','high','critical')", name="ck_finding_severity"
            ),
        )
        op.create_index("ix_findings_firm_id", "findings", ["firm_id"])
        op.create_index("ix_findings_engagement_id", "findings", ["engagement_id"])
        op.create_index(
            "ix_findings_records_firm_engagement", "findings", ["firm_id", "engagement_id"]
        )
    if "response_requests" not in tables:
        op.create_table(
            "response_requests",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("firm_id", sa.String(36), sa.ForeignKey("firms.id"), nullable=False),
            sa.Column(
                "engagement_id", sa.String(36), sa.ForeignKey("engagements.id"), nullable=False
            ),
            sa.Column("finding_id", sa.String(36), sa.ForeignKey("findings.id"), nullable=False),
            sa.Column("title", sa.String(255), nullable=False),
            sa.Column("request_text", sa.Text(), nullable=False),
            sa.Column("status", sa.String(10), nullable=False),
            sa.Column("response", sa.Text(), nullable=False),
            sa.Column("responded_at", TS, nullable=True),
            sa.Column("responded_by_id", sa.String(36), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("released_at", TS, nullable=False),
            sa.Column("released_by_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
            sa.UniqueConstraint("finding_id", name="uq_response_request_finding"),
            sa.CheckConstraint("status in ('open','responded')", name="ck_response_request_status"),
        )
        op.create_index("ix_response_requests_firm_id", "response_requests", ["firm_id"])
        op.create_index(
            "ix_response_requests_engagement_id", "response_requests", ["engagement_id"]
        )
        op.create_index(
            "ix_response_requests_firm_engagement",
            "response_requests",
            ["firm_id", "engagement_id"],
        )


def downgrade() -> None:
    op.drop_table("response_requests")
    op.drop_table("findings")
