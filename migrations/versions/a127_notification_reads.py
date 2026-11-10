"""Per-auditor read marks for derived notifications. Additive and idempotent.

Revision ID: a127_notification_reads
Revises: a126_engagement_signoffs
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "a127_notification_reads"
down_revision: str | None = "a126_engagement_signoffs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if "notification_reads" in set(inspect(op.get_bind()).get_table_names()):
        return
    op.create_table(
        "notification_reads",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("notification_id", sa.String(80), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "notification_id", name="uq_notification_read"),
    )
    op.create_index("ix_notification_reads_user_id", "notification_reads", ["user_id"])


def downgrade() -> None:
    op.drop_table("notification_reads")
