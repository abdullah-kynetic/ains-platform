"""Client representations, follow-up state and document intake feedback."""

import sqlalchemy as sa
from alembic import op

revision = "a104_client_workflow"
down_revision = "0790ed53879f"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("checklist_item_instances", sa.Column("representation", sa.String(50)))
    op.add_column(
        "checklist_item_instances",
        sa.Column("follow_up", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column("documents", sa.Column("feedback_code", sa.String(50)))


def downgrade():
    op.drop_column("documents", "feedback_code")
    op.drop_column("checklist_item_instances", "follow_up")
    op.drop_column("checklist_item_instances", "representation")
