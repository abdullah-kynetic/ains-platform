"""Persist auditor tasks and expanded pipeline statuses."""

import sqlalchemy as sa
from alembic import op

revision = "a106_auditor_tasks"
down_revision = "a105_manual_review"
branch_labels = None
depends_on = None

OLD_ENGAGEMENT_STATUS = sa.String(14)
ENGAGEMENT_STATUS = sa.Enum(
    "DRAFT",
    "COLLECTING",
    "TESTING",
    "AUDITOR_REVIEW",
    "REPORT_DRAFTING",
    "AWAITING_SIGNATURE",
    "COMPLETE",
    name="engagementstatus",
    native_enum=False,
)


def upgrade():
    op.alter_column(
        "engagements",
        "status",
        existing_type=OLD_ENGAGEMENT_STATUS,
        type_=ENGAGEMENT_STATUS,
        existing_nullable=False,
    )
    op.create_table(
        "auditor_tasks",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("firm_id", sa.String(36), nullable=False),
        sa.Column("engagement_id", sa.String(36), nullable=False),
        sa.Column("assignee_id", sa.String(36), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("request_id", sa.String(120), nullable=True),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column(
            "priority",
            sa.Enum("HIGH", "NORMAL", "LOW", name="taskpriority", native_enum=False),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_by_id", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["assignee_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["completed_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["engagement_id"], ["engagements.id"]),
        sa.ForeignKeyConstraint(["firm_id"], ["firms.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_auditor_tasks_assignee_completed",
        "auditor_tasks",
        ["assignee_id", "completed_at"],
        unique=False,
    )
    op.create_index(
        "ix_auditor_tasks_assignee_id", "auditor_tasks", ["assignee_id"], unique=False
    )
    op.create_index(
        "ix_auditor_tasks_engagement_id", "auditor_tasks", ["engagement_id"], unique=False
    )
    op.create_index(
        "ix_auditor_tasks_firm_engagement",
        "auditor_tasks",
        ["firm_id", "engagement_id"],
        unique=False,
    )
    op.create_index("ix_auditor_tasks_firm_id", "auditor_tasks", ["firm_id"], unique=False)


def downgrade():
    op.drop_table("auditor_tasks")
    op.execute(
        "UPDATE engagements SET status = 'AUDITOR_REVIEW' "
        "WHERE status IN ('REPORT_DRAFTING', 'AWAITING_SIGNATURE')"
    )
    op.alter_column(
        "engagements",
        "status",
        existing_type=ENGAGEMENT_STATUS,
        type_=OLD_ENGAGEMENT_STATUS,
        existing_nullable=False,
    )
