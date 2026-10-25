"""Allow engagement documents without a checklist request."""

import sqlalchemy as sa
from alembic import op

revision = "a111_unassigned_documents"
down_revision = "a110_audit_chain"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("documents", sa.Column("engagement_id", sa.String(36), nullable=True))
    op.create_foreign_key(
        "fk_documents_engagement", "documents", "engagements", ["engagement_id"], ["id"]
    )
    op.create_index("ix_documents_engagement_id", "documents", ["engagement_id"])
    op.execute(
        sa.text(
            "UPDATE documents SET engagement_id = (SELECT engagement_id FROM "
            "checklist_item_instances WHERE "
            "checklist_item_instances.id = documents.item_instance_id)"
        )
    )
    op.alter_column("documents", "item_instance_id", existing_type=sa.String(36), nullable=True)


def downgrade():
    # Refuse to discard unassigned documents to restore the old required request link.
    connection = op.get_bind()
    if connection.scalar(sa.text("SELECT count(*) FROM documents WHERE item_instance_id IS NULL")):
        raise RuntimeError("Assign unassigned documents before downgrading")
    op.alter_column("documents", "item_instance_id", existing_type=sa.String(36), nullable=False)
    op.drop_index("ix_documents_engagement_id", table_name="documents")
    op.drop_constraint("fk_documents_engagement", "documents", type_="foreignkey")
    op.drop_column("documents", "engagement_id")
