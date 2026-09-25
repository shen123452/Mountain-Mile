"""Group agent runs into conversation threads."""
from alembic import op
import sqlalchemy as sa

revision = "c8e4b7d2a915"
down_revision = "b7f2a9c4d310"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("agent_runs", sa.Column("thread_id", sa.String(32), nullable=False, server_default="legacy", index=True))


def downgrade() -> None:
    op.drop_column("agent_runs", "thread_id")
