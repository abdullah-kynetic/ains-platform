"""Add independent auditor invoicing tables; existing tables and data are untouched."""

import sqlalchemy as sa
from alembic import op

revision = "a112_auditor_invoices"
down_revision = "a111_unassigned_documents"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "invoice_issuers",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("firm_id", sa.String(36), sa.ForeignKey("firms.id"), unique=True),
        sa.Column("auditor_id", sa.String(36), sa.ForeignKey("users.id"), unique=True),
        sa.Column("next_number", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "(firm_id IS NULL) <> (auditor_id IS NULL)", name="ck_invoice_issuer_owner"
        ),
    )
    op.create_table(
        "invoices",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("issuer_id", sa.String(36), sa.ForeignKey("invoice_issuers.id"), nullable=False),
        sa.Column("firm_id", sa.String(36), sa.ForeignKey("firms.id"), nullable=False),
        sa.Column("engagement_id", sa.String(36), sa.ForeignKey("engagements.id")),
        sa.Column("auditor_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(12), nullable=False),
        sa.Column("issue_date", sa.Date(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("subtotal_cents", sa.BigInteger(), nullable=False),
        sa.Column("total_cents", sa.BigInteger(), nullable=False),
        sa.Column("amount_paid_cents", sa.BigInteger(), nullable=False),
        sa.Column("paid_at", sa.Date()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("issuer_id", "number", name="uq_invoice_issuer_number"),
        sa.CheckConstraint("status IN ('draft', 'sent', 'paid', 'void')", name="ck_invoice_status"),
        sa.CheckConstraint("due_date >= issue_date", name="ck_invoice_dates"),
        sa.CheckConstraint(
            "total_cents > 0 AND subtotal_cents = total_cents AND "
            "amount_paid_cents >= 0 AND amount_paid_cents <= total_cents",
            name="ck_invoice_amounts",
        ),
    )
    op.create_index("ix_invoice_scope_status_due", "invoices", ["issuer_id", "status", "due_date"])
    op.create_index("ix_invoice_client_issue", "invoices", ["firm_id", "issue_date"])
    op.create_index("ix_invoices_engagement_id", "invoices", ["engagement_id"])
    op.create_index("ix_invoices_auditor_id", "invoices", ["auditor_id"])
    op.create_table(
        "invoice_line_items",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("invoice_id", sa.String(36), sa.ForeignKey("invoices.id"), nullable=False),
        sa.Column("description", sa.String(1000), nullable=False),
        sa.Column("quantity", sa.Numeric(12, 2), nullable=False),
        sa.Column("rate_cents", sa.BigInteger(), nullable=False),
        sa.Column("amount_cents", sa.BigInteger(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.UniqueConstraint("invoice_id", "position", name="uq_invoice_line_position"),
        sa.CheckConstraint(
            "quantity > 0 AND rate_cents >= 0 AND amount_cents >= 0", name="ck_invoice_line_amounts"
        ),
    )
    op.create_index("ix_invoice_line_items_invoice_id", "invoice_line_items", ["invoice_id"])
    op.create_table(
        "invoice_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("invoice_id", sa.String(36), sa.ForeignKey("invoices.id"), nullable=False),
        sa.Column("type", sa.String(32), nullable=False),
        sa.Column("from_status", sa.String(12)),
        sa.Column("to_status", sa.String(12), nullable=False),
        sa.Column("amount_cents", sa.BigInteger()),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actor_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
    )
    op.create_index("ix_invoice_events_invoice_id", "invoice_events", ["invoice_id"])


def downgrade():
    # A deployed financial ledger is retained for image rollback. No destructive downgrade.
    raise RuntimeError("Invoice ledger must be retained; roll back the application image instead")
