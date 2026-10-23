"""Add single-use client workspace invitations."""

import sqlalchemy as sa
from alembic import op

revision = "a107_client_invitations"
down_revision = "a106_auditor_tasks"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "client_invitations",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("firm_id", sa.String(36), nullable=False),
        sa.Column("engagement_id", sa.String(36), nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by_id", sa.String(36), nullable=False),
        sa.Column("accepted_user_id", sa.String(36), nullable=True),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["accepted_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["engagement_id"], ["engagements.id"]),
        sa.ForeignKeyConstraint(["firm_id"], ["firms.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("accepted_user_id"),
        sa.UniqueConstraint("email", name="uq_client_invitations_email"),
    )
    op.create_index(
        "ix_client_invitations_email", "client_invitations", ["email"], unique=False
    )
    op.create_index(
        "ix_client_invitations_engagement_id",
        "client_invitations",
        ["engagement_id"],
        unique=False,
    )
    op.create_index(
        "ix_client_invitations_expires_at",
        "client_invitations",
        ["expires_at"],
        unique=False,
    )
    op.create_index(
        "ix_client_invitations_firm_engagement",
        "client_invitations",
        ["firm_id", "engagement_id"],
        unique=False,
    )
    op.create_index(
        "ix_client_invitations_firm_id", "client_invitations", ["firm_id"], unique=False
    )
    op.create_index(
        "ix_client_invitations_created_by_id",
        "client_invitations",
        ["created_by_id"],
        unique=False,
    )
    op.create_index(
        "ix_client_invitations_token_hash",
        "client_invitations",
        ["token_hash"],
        unique=True,
    )


def downgrade():
    op.drop_table("client_invitations")
