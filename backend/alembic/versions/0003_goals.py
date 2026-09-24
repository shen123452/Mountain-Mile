"""Create goals."""
from alembic import op
import sqlalchemy as sa

revision = "0003_goals"
down_revision = "0002_auth"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "goals",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("user_id", sa.String(32), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("category", sa.String(20), nullable=False, server_default="other"),
        sa.Column("palette_variant", sa.String(20), nullable=False, server_default="jade"),
        sa.Column("seed", sa.String(32), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("weekly_target_minutes", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("start_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_goals_user_status", "goals", ["user_id", "status"])


def downgrade() -> None:
    op.drop_table("goals")
