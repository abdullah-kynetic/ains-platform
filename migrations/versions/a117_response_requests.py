"""Add explicit auditor release fields for client "Responses requested" (additive, nullable)."""

import sqlalchemy as sa
from alembic import op

revision = "a117_response_requests"
down_revision = "a116_client_profiles"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("checklist_item_instances") as batch:
        batch.add_column(sa.Column("response_request_text", sa.Text(), nullable=True))
        batch.add_column(
            sa.Column("response_released_at", sa.DateTime(timezone=True), nullable=True)
        )
        batch.add_column(sa.Column("response_released_by_id", sa.String(36), nullable=True))


def downgrade():
    with op.batch_alter_table("checklist_item_instances") as batch:
        batch.drop_column("response_released_by_id")
        batch.drop_column("response_released_at")
        batch.drop_column("response_request_text")
