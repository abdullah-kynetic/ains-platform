"""Per-user first sign-in walkthrough state; existing users start pending."""

import sqlalchemy as sa
from alembic import op

revision = "a115_user_onboarding"
down_revision = "a114_engagement_reports"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("onboarding_state", sa.String(12)))
    op.add_column("users", sa.Column("onboarding_finished_at", sa.DateTime(timezone=True)))


def downgrade():
    raise RuntimeError("Retain onboarding preferences during image rollback")
