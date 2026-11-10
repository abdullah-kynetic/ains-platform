"""Optional public logo URL on firms.

Nullable. Branding responses copy this value and no other firm columns.

Revision ID: a119_firm_logo_url
Revises: a118_firm_portal_slug
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "a119_firm_logo_url"
down_revision: str | None = "a118_firm_portal_slug"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    columns = {column["name"] for column in inspect(op.get_bind()).get_columns("firms")}
    if "logo_url" not in columns:
        op.add_column("firms", sa.Column("logo_url", sa.String(length=500), nullable=True))


def downgrade() -> None:
    columns = {column["name"] for column in inspect(op.get_bind()).get_columns("firms")}
    if "logo_url" in columns:
        op.drop_column("firms", "logo_url")
