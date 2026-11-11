"""Emailed sign-in codes and remembered devices. Additive, idempotent.

Revision ID: a129_email_sign_in_codes
Revises: a128_practice_signoff_setting
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "a129_email_sign_in_codes"
down_revision: str | None = "a128_practice_signoff_setting"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    tables = set(inspect(op.get_bind()).get_table_names())
    if "email_sign_in_codes" not in tables:
        op.create_table(
            "email_sign_in_codes",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("firm_id", sa.String(36), sa.ForeignKey("firms.id")),
            sa.Column("code_hash", sa.String(64), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("used_at", sa.DateTime(timezone=True)),
            sa.Column("revoked_at", sa.DateTime(timezone=True)),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_email_sign_in_codes_user_id", "email_sign_in_codes", ["user_id"])
        op.create_index("ix_email_sign_in_codes_firm_id", "email_sign_in_codes", ["firm_id"])
        op.create_index("ix_email_sign_in_codes_expires_at", "email_sign_in_codes", ["expires_at"])
        op.create_index(
            "ix_email_sign_in_codes_user_created", "email_sign_in_codes", ["user_id", "created_at"]
        )
    if "trusted_devices" not in tables:
        op.create_table(
            "trusted_devices",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("firm_id", sa.String(36), sa.ForeignKey("firms.id")),
            sa.Column("token_hash", sa.String(64), nullable=False),
            sa.Column("user_agent", sa.String(200)),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("last_used_at", sa.DateTime(timezone=True)),
            sa.Column("revoked_at", sa.DateTime(timezone=True)),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_trusted_devices_user_id", "trusted_devices", ["user_id"])
        op.create_index("ix_trusted_devices_firm_id", "trusted_devices", ["firm_id"])
        op.create_index("ix_trusted_devices_expires_at", "trusted_devices", ["expires_at"])
        op.create_index(
            "ix_trusted_devices_token_hash", "trusted_devices", ["token_hash"], unique=True
        )


def downgrade() -> None:
    op.drop_table("trusted_devices")
    op.drop_table("email_sign_in_codes")
