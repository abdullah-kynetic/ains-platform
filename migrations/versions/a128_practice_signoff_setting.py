"""Per-practice setting: may the assigned auditor also sign as the partner. Additive, idempotent.

Revision ID: a128_practice_signoff_setting
Revises: a127_notification_reads
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "a128_practice_signoff_setting"
down_revision: str | None = "a127_notification_reads"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    columns = {c["name"] for c in inspect(op.get_bind()).get_columns("practices")}
    if "allow_auditor_as_signer" in columns:
        return
    op.add_column(
        "practices",
        sa.Column(
            "allow_auditor_as_signer", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
    )


def downgrade() -> None:
    with op.batch_alter_table("practices") as batch:
        batch.drop_column("allow_auditor_as_signer")
