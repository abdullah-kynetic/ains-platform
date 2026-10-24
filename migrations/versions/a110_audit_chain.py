"""Chain historical audit entries and enforce append-only storage."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.orm import Session

from app.audit import GENESIS, digest
from app.database.models import AuditLog

revision = "a110_audit_chain"
down_revision = "a109_password_reset"
branch_labels = None
depends_on = None


def upgrade():
    for name, kind in [
        ("ip_address", sa.String(45)),
        ("sequence", sa.Integer()),
        ("previous_hash", sa.String(64)),
        ("row_hash", sa.String(64)),
    ]:
        op.add_column("audit_logs", sa.Column(name, kind, nullable=True))
    connection = op.get_bind()
    with Session(connection) as session:
        heads = {}
        rows = session.scalars(sa.select(AuditLog).order_by(AuditLog.created_at, AuditLog.id)).all()
        for row in rows:
            sequence, previous = heads.get(row.firm_id, (0, GENESIS))
            row.sequence, row.previous_hash = sequence + 1, previous
            row.row_hash = digest(row)
            # Core update deliberately bypasses ORM immutability during backfill.
            connection.execute(
                sa.update(AuditLog.__table__)
                .where(AuditLog.id == row.id)
                .values(
                    sequence=row.sequence, previous_hash=row.previous_hash, row_hash=row.row_hash
                )
            )
    with op.batch_alter_table("audit_logs") as batch:
        for name in ("sequence", "previous_hash", "row_hash"):
            batch.alter_column(name, nullable=False)
        batch.create_unique_constraint("uq_audit_firm_sequence", ["firm_id", "sequence"])
    if connection.dialect.name == "postgresql":
        op.execute("""CREATE FUNCTION reject_audit_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN RAISE EXCEPTION 'Audit log is append-only'; END; $$""")
        op.execute("""CREATE TRIGGER audit_log_immutable BEFORE UPDATE OR DELETE OR TRUNCATE
        ON audit_logs FOR EACH STATEMENT EXECUTE FUNCTION reject_audit_mutation()""")


def downgrade():
    if op.get_bind().dialect.name == "postgresql":
        op.execute("DROP TRIGGER audit_log_immutable ON audit_logs")
        op.execute("DROP FUNCTION reject_audit_mutation()")
    with op.batch_alter_table("audit_logs") as batch:
        batch.drop_constraint("uq_audit_firm_sequence", type_="unique")
        for name in ("ip_address", "sequence", "previous_hash", "row_hash"):
            batch.drop_column(name)
