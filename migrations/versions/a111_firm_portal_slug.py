"""Enforce firms.slug as a unique lowercase portal label.

``firms.slug`` already exists (unique index from the initial schema). This
revision does not add a second column. On PostgreSQL it lowercases existing
values and rejects anything that is not a single DNS label, including the
reserved hosts www, api, app, admin, mail and status.

Revision ID: a111_firm_portal_slug
Revises: a110_audit_chain
"""

from collections.abc import Sequence

from alembic import op

revision: str = "a111_firm_portal_slug"
down_revision: str | None = "a110_audit_chain"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_CHECK = (
    "slug ~ '^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$'"
    " AND slug NOT IN ('www', 'api', 'app', 'admin', 'mail', 'status')"
)


def upgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    op.execute("UPDATE firms SET slug = lower(slug) WHERE slug <> lower(slug)")
    op.create_check_constraint("ck_firms_portal_slug", "firms", _CHECK)


def downgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    op.drop_constraint("ck_firms_portal_slug", "firms", type_="check")
