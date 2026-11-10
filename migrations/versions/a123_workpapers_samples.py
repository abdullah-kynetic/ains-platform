"""Workpapers and sample sets (auditor-only, per engagement). Additive and idempotent.

Revision ID: a123_workpapers_samples
Revises: a122_checklist_conclusions
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "a123_workpapers_samples"
down_revision: str | None = "a122_checklist_conclusions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TS = sa.DateTime(timezone=True)


def _fk(target: str) -> sa.ForeignKey:
    return sa.ForeignKey(target)


def upgrade() -> None:
    tables = set(inspect(op.get_bind()).get_table_names())
    if "workpapers" not in tables:
        op.create_table(
            "workpapers",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("firm_id", sa.String(36), _fk("firms.id"), nullable=False),
            sa.Column("engagement_id", sa.String(36), _fk("engagements.id"), nullable=False),
            sa.Column("request_id", sa.String(20), nullable=False),
            sa.Column("procedure", sa.Text(), nullable=False),
            sa.Column("evidence_ids", sa.JSON(), nullable=False),
            sa.Column("conclusion", sa.String(8), nullable=True),
            sa.Column("preparer_id", sa.String(36), _fk("users.id"), nullable=False),
            sa.Column("prepared_at", TS, nullable=False),
            sa.Column("reviewer_id", sa.String(36), _fk("users.id"), nullable=True),
            sa.Column("reviewed_at", TS, nullable=True),
            sa.UniqueConstraint(
                "engagement_id", "request_id", name="uq_workpaper_engagement_request"
            ),
        )
        op.create_index("ix_workpapers_firm_id", "workpapers", ["firm_id"])
        op.create_index("ix_workpapers_engagement_id", "workpapers", ["engagement_id"])
        op.create_index("ix_workpapers_firm_engagement", "workpapers", ["firm_id", "engagement_id"])
    if "sample_sets" not in tables:
        op.create_table(
            "sample_sets",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("firm_id", sa.String(36), _fk("firms.id"), nullable=False),
            sa.Column("engagement_id", sa.String(36), _fk("engagements.id"), nullable=False),
            sa.Column("area", sa.String(200), nullable=False),
            sa.Column("request_id", sa.String(20), nullable=True),
            sa.Column("population", sa.Integer(), nullable=False),
            sa.Column("sample_size", sa.Integer(), nullable=False),
            sa.Column("method", sa.String(200), nullable=False),
            sa.Column("created_by_id", sa.String(36), _fk("users.id"), nullable=False),
            sa.Column("created_at", TS, nullable=False),
        )
        op.create_index("ix_sample_sets_firm_id", "sample_sets", ["firm_id"])
        op.create_index("ix_sample_sets_engagement_id", "sample_sets", ["engagement_id"])
        op.create_index(
            "ix_sample_sets_firm_engagement", "sample_sets", ["firm_id", "engagement_id"]
        )
    if "sample_items" not in tables:
        op.create_table(
            "sample_items",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("firm_id", sa.String(36), _fk("firms.id"), nullable=False),
            sa.Column("set_id", sa.String(36), _fk("sample_sets.id"), nullable=False),
            sa.Column("position", sa.Integer(), nullable=False),
            sa.Column("reference", sa.String(64), nullable=False),
            sa.Column("result", sa.String(10), nullable=False),
            sa.Column("note", sa.Text(), nullable=False),
            sa.Column("updated_by_id", sa.String(36), _fk("users.id"), nullable=True),
            sa.Column("updated_at", TS, nullable=True),
            sa.CheckConstraint(
                "result in ('pending','pass','exception')", name="ck_sample_item_result"
            ),
        )
        op.create_index("ix_sample_items_firm_id", "sample_items", ["firm_id"])
        op.create_index("ix_sample_items_set_id", "sample_items", ["set_id"])
        op.create_index("ix_sample_items_firm_set", "sample_items", ["firm_id", "set_id"])


def downgrade() -> None:
    op.drop_table("sample_items")
    op.drop_table("sample_sets")
    op.drop_table("workpapers")
