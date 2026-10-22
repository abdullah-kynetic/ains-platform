"""Separate human applicability and evidence assessment."""

import sqlalchemy as sa
from alembic import op

revision = "a105_manual_review"
down_revision = "a104_client_workflow"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("checklist_item_instances", sa.Column("applicability_decision", sa.String(30)))
    op.add_column("checklist_item_instances", sa.Column("assessment", sa.String(30)))
    op.add_column(
        "checklist_item_instances",
        sa.Column("internal_notes", sa.Text(), nullable=False, server_default=""),
    )


def downgrade():
    op.drop_column("checklist_item_instances", "internal_notes")
    op.drop_column("checklist_item_instances", "assessment")
    op.drop_column("checklist_item_instances", "applicability_decision")
