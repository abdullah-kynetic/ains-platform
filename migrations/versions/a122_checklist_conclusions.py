"""Auditor's per-request test conclusion on checklist items (human-entered, nullable).

Additive and idempotent.

Revision ID: a122_checklist_conclusions
Revises: a121_practice_routes
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "a122_checklist_conclusions"
down_revision: str | None = "a121_practice_routes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE = "checklist_item_instances"


def upgrade() -> None:
    existing = {c["name"] for c in inspect(op.get_bind()).get_columns(TABLE)}
    columns = [
        sa.Column("conclusion", sa.String(8), nullable=True),
        sa.Column("conclusion_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("conclusion_updated_by_id", sa.String(36), nullable=True),
    ]
    missing = [c for c in columns if c.name not in existing]
    if missing:
        with op.batch_alter_table(TABLE) as batch:
            for column in missing:
                batch.add_column(column)


def downgrade() -> None:
    with op.batch_alter_table(TABLE) as batch:
        batch.drop_column("conclusion_updated_by_id")
        batch.drop_column("conclusion_updated_at")
        batch.drop_column("conclusion")
