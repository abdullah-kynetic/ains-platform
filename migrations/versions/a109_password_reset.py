"""Password reset tokens and shared request throttles."""

import sqlalchemy as sa
from alembic import op

revision = "a109_password_reset"
down_revision = "8ad73a592bc1"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "password_reset_tokens",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True)),
    )
    for column in ("user_id", "token_hash", "expires_at"):
        op.create_index(
            f"ix_password_reset_tokens_{column}",
            "password_reset_tokens",
            [column],
            unique=column == "token_hash",
        )
    op.create_table(
        "auth_rate_limits",
        sa.Column("key", sa.String(64), primary_key=True),
        sa.Column("count", sa.Integer, nullable=False),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade():
    op.drop_table("auth_rate_limits")
    op.drop_table("password_reset_tokens")
