"""Add reversible NA snapshot. Status is an existing non-native VARCHAR enum."""
import sqlalchemy as sa
from alembic import op

revision = "a113_checklist_na"
down_revision = "a112_auditor_invoices"
branch_labels = None
depends_on = None


def upgrade():
    # No PostgreSQL enum ALTER: ClientStatus uses native_enum=False and the
    # new name fits the existing VARCHAR. Nullable JSON preserves existing rows.
    op.add_column("checklist_item_instances", sa.Column("na_previous_state", sa.JSON()))


def downgrade():
    raise RuntimeError("Retain applicability history during image rollback")
