"""Quentin's workflow: dispatch, reasoned N/A, document numbers, links and issue threads.

Additive. Existing engagements outside draft are treated as already dispatched and existing
documents are numbered ``1.<n>`` per engagement in upload order.

Revision ID: a120_workflow_routes
Revises: a119_firm_logo_url
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "a120_workflow_routes"
down_revision: str | None = "a119_firm_logo_url"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TS = sa.DateTime(timezone=True)


def upgrade() -> None:
    with op.batch_alter_table("engagements") as batch:
        batch.add_column(sa.Column("checklist_sent_at", TS, nullable=True))
        batch.add_column(sa.Column("checklist_sent_by_id", sa.String(36), nullable=True))
        batch.add_column(sa.Column("client_submitted_at", TS, nullable=True))
        batch.add_column(sa.Column("report_confirmed_at", TS, nullable=True))
        batch.add_column(sa.Column("report_confirmed_by_id", sa.String(36), nullable=True))
        batch.add_column(sa.Column("report_confirmed_sha256", sa.String(64), nullable=True))
        batch.add_column(
            sa.Column("document_seq", sa.Integer(), nullable=False, server_default="0")
        )
    with op.batch_alter_table("checklist_item_instances") as batch:
        batch.add_column(sa.Column("na_request_reason", sa.Text(), nullable=True))
        batch.add_column(sa.Column("na_decision_note", sa.Text(), nullable=True))
        batch.add_column(sa.Column("na_decided_at", TS, nullable=True))
        batch.add_column(sa.Column("submitted_at", TS, nullable=True))
        batch.add_column(sa.Column("submitted_by_id", sa.String(36), nullable=True))
    with op.batch_alter_table("documents") as batch:
        batch.add_column(sa.Column("number", sa.String(20), nullable=True))
        batch.create_unique_constraint(
            "uq_document_engagement_number", ["engagement_id", "number"]
        )

    bind = op.get_bind()
    bind.execute(
        sa.text(
            "UPDATE engagements SET checklist_sent_at = created_at WHERE upper(status) <> 'DRAFT'"
        )
    )
    engagements = bind.execute(sa.text("SELECT id FROM engagements")).scalars().all()
    for engagement_id in engagements:
        rows = bind.execute(
            sa.text(
                "SELECT id FROM documents WHERE engagement_id = :e ORDER BY created_at, id"
            ),
            {"e": engagement_id},
        ).scalars().all()
        for sequence, document_id in enumerate(rows, 1):
            bind.execute(
                sa.text("UPDATE documents SET number = :n WHERE id = :d"),
                {"n": f"1.{sequence}", "d": document_id},
            )
        bind.execute(
            sa.text("UPDATE engagements SET document_seq = :n WHERE id = :e"),
            {"n": len(rows), "e": engagement_id},
        )

    op.create_table(
        "document_item_links",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("firm_id", sa.String(36), sa.ForeignKey("firms.id"), nullable=False),
        sa.Column("engagement_id", sa.String(36), sa.ForeignKey("engagements.id"), nullable=False),
        sa.Column(
            "item_instance_id",
            sa.String(36),
            sa.ForeignKey("checklist_item_instances.id"),
            nullable=False,
        ),
        sa.Column("document_id", sa.String(36), sa.ForeignKey("documents.id"), nullable=False),
        sa.Column("linked_by_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", TS, nullable=False),
        sa.UniqueConstraint("item_instance_id", "document_id", name="uq_document_item_link"),
    )
    op.create_index("ix_document_item_links_firm_id", "document_item_links", ["firm_id"])
    op.create_index(
        "ix_document_item_links_engagement_id", "document_item_links", ["engagement_id"]
    )
    op.create_index(
        "ix_document_item_links_item_instance_id", "document_item_links", ["item_instance_id"]
    )
    op.create_index("ix_document_item_links_document_id", "document_item_links", ["document_id"])
    op.create_index(
        "ix_document_item_links_firm_engagement",
        "document_item_links",
        ["firm_id", "engagement_id"],
    )

    op.create_table(
        "document_issues",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("firm_id", sa.String(36), sa.ForeignKey("firms.id"), nullable=False),
        sa.Column("engagement_id", sa.String(36), sa.ForeignKey("engagements.id"), nullable=False),
        sa.Column(
            "item_instance_id",
            sa.String(36),
            sa.ForeignKey("checklist_item_instances.id"),
            nullable=False,
        ),
        sa.Column("document_id", sa.String(36), sa.ForeignKey("documents.id"), nullable=True),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("status", sa.String(12), nullable=False),
        sa.Column("created_by_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("resolved_by_id", sa.String(36), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("resolved_at", TS, nullable=True),
        sa.Column("created_at", TS, nullable=False),
        sa.CheckConstraint(
            "kind IN ('outdated', 'wrong_year', 'incorrect', 'missing')", name="ck_issue_kind"
        ),
        sa.CheckConstraint("status IN ('open', 'resolved')", name="ck_issue_status"),
    )
    op.create_index("ix_document_issues_firm_id", "document_issues", ["firm_id"])
    op.create_index("ix_document_issues_engagement_id", "document_issues", ["engagement_id"])
    op.create_index(
        "ix_document_issues_item_instance_id", "document_issues", ["item_instance_id"]
    )
    op.create_index("ix_document_issues_document_id", "document_issues", ["document_id"])
    op.create_index(
        "ix_document_issues_firm_engagement", "document_issues", ["firm_id", "engagement_id"]
    )
    op.create_index(
        "ix_document_issues_item_status", "document_issues", ["item_instance_id", "status"]
    )

    op.create_table(
        "issue_messages",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("firm_id", sa.String(36), sa.ForeignKey("firms.id"), nullable=False),
        sa.Column("issue_id", sa.String(36), sa.ForeignKey("document_issues.id"), nullable=False),
        sa.Column("author_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("author_role", sa.String(12), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("document_id", sa.String(36), sa.ForeignKey("documents.id"), nullable=True),
        sa.Column("created_at", TS, nullable=False),
    )
    op.create_index("ix_issue_messages_firm_id", "issue_messages", ["firm_id"])
    op.create_index("ix_issue_messages_issue_id", "issue_messages", ["issue_id"])
    op.create_index("ix_issue_messages_firm_issue", "issue_messages", ["firm_id", "issue_id"])


def downgrade() -> None:
    for name in ("issue_messages", "document_issues", "document_item_links"):
        if name in inspect(op.get_bind()).get_table_names():
            op.drop_table(name)
    with op.batch_alter_table("documents") as batch:
        batch.drop_constraint("uq_document_engagement_number", type_="unique")
        batch.drop_column("number")
    with op.batch_alter_table("checklist_item_instances") as batch:
        for column in (
            "submitted_by_id",
            "submitted_at",
            "na_decided_at",
            "na_decision_note",
            "na_request_reason",
        ):
            batch.drop_column(column)
    with op.batch_alter_table("engagements") as batch:
        for column in (
            "document_seq",
            "report_confirmed_sha256",
            "report_confirmed_by_id",
            "report_confirmed_at",
            "client_submitted_at",
            "checklist_sent_by_id",
            "checklist_sent_at",
        ):
            batch.drop_column(column)
