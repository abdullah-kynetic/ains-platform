"""Add expiring auditor MFA enrollment and single-use recovery codes."""

import sqlalchemy as sa
from alembic import op

revision = "a108_auditor_mfa_recovery"
down_revision = "a107_client_invitations"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "users",
        sa.Column("mfa_enrollment_expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "mfa_recovery_codes",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("code_hash", sa.String(64), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_mfa_recovery_codes_code_hash",
        "mfa_recovery_codes",
        ["code_hash"],
        unique=True,
    )
    op.create_index(
        "ix_mfa_recovery_codes_user_active",
        "mfa_recovery_codes",
        ["user_id", "used_at", "revoked_at"],
        unique=False,
    )
    op.create_index(
        "ix_mfa_recovery_codes_user_id",
        "mfa_recovery_codes",
        ["user_id"],
        unique=False,
    )


def downgrade():
    op.drop_table("mfa_recovery_codes")
    op.drop_column("users", "mfa_enrollment_expires_at")
