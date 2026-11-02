"""Add client profile metadata and contacts without changing existing tables."""

import sqlalchemy as sa
from alembic import op

revision = "a116_client_profiles"
down_revision = "a115_user_onboarding"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "client_profile_details",
        sa.Column("firm_id", sa.String(36), sa.ForeignKey("firms.id"), primary_key=True),
        sa.Column("firm_type", sa.String(120), nullable=False),
        sa.Column("crd", sa.String(40), nullable=False),
        sa.Column("clearing", sa.String(255), nullable=False),
        sa.Column("state", sa.String(120), nullable=False),
    )
    op.create_table(
        "client_contacts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("firm_id", sa.String(36), sa.ForeignKey("firms.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("phone", sa.String(80), nullable=False),
        sa.Column("primary", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_client_contacts_firm_id", "client_contacts", ["firm_id"])


def downgrade():
    op.drop_index("ix_client_contacts_firm_id", table_name="client_contacts")
    op.drop_table("client_contacts")
    op.drop_table("client_profile_details")
