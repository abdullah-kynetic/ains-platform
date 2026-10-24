"""Freeze checklist versions on engagements.

Revision ID: 8ad73a592bc1
Revises: a108_auditor_mfa_recovery
"""

import sqlalchemy as sa
from alembic import op

revision = "8ad73a592bc1"
down_revision = "a108_auditor_mfa_recovery"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("engagements", sa.Column("checklist_version", sa.String(120), nullable=True))
    op.add_column("engagements", sa.Column("checklist_snapshot", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("engagements", "checklist_snapshot")
    op.drop_column("engagements", "checklist_version")
