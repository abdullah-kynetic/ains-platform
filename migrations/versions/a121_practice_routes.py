"""Auditing practice: team membership, branding, rubric overrides and request templates.

Additive and idempotent (Postgres CI builds the schema from the models before migrating).
Existing auditors join one default practice; the earliest-created auditor becomes its partner
so someone can invite the rest. Clients are untouched.

Revision ID: a121_practice_routes
Revises: a120_workflow_routes
"""

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "a121_practice_routes"
down_revision: str | None = "a120_workflow_routes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TS = sa.DateTime(timezone=True)


def _create_tables() -> None:
    tables = set(inspect(op.get_bind()).get_table_names())
    if "practices" not in tables:
        op.create_table(
            "practices",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("name", sa.String(120), nullable=False),
            sa.Column("tagline", sa.String(200), nullable=False, server_default=""),
            sa.Column("logo_url", sa.String(500), nullable=True),
            sa.Column("created_at", TS, nullable=False),
        )
    if "practice_rubric_items" not in tables:
        op.create_table(
            "practice_rubric_items",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("practice_id", sa.String(36), sa.ForeignKey("practices.id"), nullable=False),
            sa.Column("request_id", sa.String(20), nullable=False),
            sa.Column("criteria", sa.Text(), nullable=False, server_default=""),
            sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("updated_by_id", sa.String(36), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("updated_at", TS, nullable=False),
            sa.UniqueConstraint("practice_id", "request_id", name="uq_practice_rubric"),
        )
        op.create_index(
            "ix_practice_rubric_items_practice_id", "practice_rubric_items", ["practice_id"]
        )
    if "practice_templates" not in tables:
        op.create_table(
            "practice_templates",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("practice_id", sa.String(36), sa.ForeignKey("practices.id"), nullable=False),
            sa.Column("name", sa.String(120), nullable=False),
            sa.Column("kind", sa.String(12), nullable=False),
            sa.Column("description", sa.String(500), nullable=False, server_default=""),
            sa.Column("request_ids", sa.JSON(), nullable=False),
            sa.Column("created_at", TS, nullable=False),
        )
        op.create_index("ix_practice_templates_practice", "practice_templates", ["practice_id"])


def upgrade() -> None:
    _create_tables()
    bind = op.get_bind()
    existing = {c["name"] for c in inspect(bind).get_columns("users")}
    missing = [
        c
        for c in (
            sa.Column("practice_id", sa.String(36), nullable=True),
            sa.Column("team_role", sa.String(12), nullable=True),
        )
        if c.name not in existing
    ]
    if missing:
        with op.batch_alter_table("users") as batch:
            for column in missing:
                batch.add_column(column)
            if any(c.name == "practice_id" for c in missing):
                batch.create_foreign_key("fk_users_practice", "practices", ["practice_id"], ["id"])
                batch.create_index("ix_users_practice_id", ["practice_id"])

    auditors = (
        bind.execute(
            sa.text(
                "SELECT id FROM users WHERE upper(role) = 'AUDITOR' AND practice_id IS NULL "
                "ORDER BY created_at, id"
            )
        )
        .scalars()
        .all()
    )
    if not auditors:
        return
    practice_id = bind.execute(
        sa.text("SELECT id FROM practices ORDER BY created_at, id LIMIT 1")
    ).scalar()
    has_partner = False
    if practice_id is None:
        practice_id = str(uuid.uuid4())
        bind.execute(
            sa.text(
                "INSERT INTO practices (id, name, tagline, created_at) "
                "VALUES (:id, 'Audit practice', '', :now)"
            ),
            {"id": practice_id, "now": datetime.now(UTC)},
        )
    else:
        has_partner = bool(
            bind.execute(
                sa.text(
                    "SELECT 1 FROM users WHERE practice_id = :p AND team_role = 'partner' LIMIT 1"
                ),
                {"p": practice_id},
            ).scalar()
        )
    for index, user_id in enumerate(auditors):
        role = "partner" if index == 0 and not has_partner else "auditor"
        bind.execute(
            sa.text("UPDATE users SET practice_id = :p, team_role = :r WHERE id = :u"),
            {"p": practice_id, "r": role, "u": user_id},
        )


def downgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.drop_index("ix_users_practice_id")
        batch.drop_column("team_role")
        batch.drop_column("practice_id")
    op.drop_table("practice_templates")
    op.drop_table("practice_rubric_items")
    op.drop_table("practices")
