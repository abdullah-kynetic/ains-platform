"""Verify additive migration parity and serialized issuer numbering on real Postgres."""

from concurrent.futures import ThreadPoolExecutor
from datetime import date

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import inspect, select
from sqlalchemy.orm import Session

from app.database.models import Base, Engagement, Firm, Invoice, User, UserRole
from app.invoicing import InvoiceInput, LineInput, create_invoice
from tests.test_audit_postgres import postgres_engine as postgres_engine


def test_additive_invoice_migration_and_concurrent_numbering(postgres_engine):
    engine = postgres_engine
    tables = [
        table
        for name, table in Base.metadata.tables.items()
        if name not in {"invoice_issuers", "invoices", "invoice_line_items", "invoice_events"}
    ]
    Base.metadata.create_all(engine, tables=tables)
    with Session(engine) as db:
        issuer = Firm(name="Synthetic audit firm", slug="synthetic-audit")
        client = Firm(name="Synthetic client", slug="synthetic-client")
        db.add_all([issuer, client])
        db.flush()
        user = User(
            name="Synthetic auditor",
            email="synthetic@example.test",
            firm_id=issuer.id,
            role=UserRole.AUDITOR,
        )
        db.add(user)
        db.flush()
        engagement = Engagement(
            firm_id=client.id,
            auditor_id=user.id,
            review_period_start=date(2025, 1, 1),
            review_period_end=date(2025, 12, 31),
        )
        db.add(engagement)
        db.commit()
        user_id, firm_id, engagement_id = user.id, client.id, engagement.id
    with engine.begin() as connection:
        original = set(inspect(connection).get_table_names())
        config = Config("alembic.ini")
        config.attributes["connection"] = connection
        command.stamp(config, "a111_unassigned_documents")
        command.upgrade(config, "a112_auditor_invoices")
        assert set(inspect(connection).get_table_names()) - original == {
            "alembic_version",
            "invoice_issuers",
            "invoices",
            "invoice_line_items",
            "invoice_events",
        }
        assert compare_metadata(MigrationContext.configure(connection), Base.metadata) == []

    def create(index):
        with Session(engine) as db:
            user = db.get(User, user_id)
            invoice = create_invoice(
                db,
                user,
                InvoiceInput(
                    firm_id=firm_id,
                    engagement_id=engagement_id,
                    issue_date=date(2026, 1, 1),
                    due_date=date(2026, 2, 1),
                    line_items=[
                        LineInput(description=f"Synthetic {index}", quantity="1", rate_cents=100)
                    ],
                ),
            )
            db.commit()
            return invoice.number

    with ThreadPoolExecutor(max_workers=4) as pool:
        assert sorted(pool.map(create, range(8))) == list(range(1, 9))
    with Session(engine) as db:
        assert len(db.scalars(select(Invoice)).all()) == 8
        assert db.get(User, user_id).email == "synthetic@example.test"
