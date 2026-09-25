"""Add archived flag to agent runs."""
from alembic import op
import sqlalchemy as sa

revision = "b7f2a9c4d310"
down_revision = "a3d8c1e5f207"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("agent_runs", sa.Column("archived", sa.Boolean(), nullable=False, server_default=sa.text("false")))


def downgrade() -> None:
    op.drop_column("agent_runs", "archived")
