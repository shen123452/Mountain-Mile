"""Add review items and run token usage."""
from alembic import op
import sqlalchemy as sa

revision = "a3d8c1e5f207"
down_revision = "ff91c5e4a102"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("review_items",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("user_id", sa.String(32), nullable=False),
        sa.Column("goal_id", sa.String(32), nullable=True),
        sa.Column("knowledge_point", sa.String(500), nullable=False),
        sa.Column("ease", sa.Float(), nullable=False, server_default="2.5"),
        sa.Column("interval_days", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("repetitions", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("last_quality", sa.Integer(), nullable=True),
        sa.Column("last_reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["goal_id"], ["goals.id"], ondelete="SET NULL"))
    op.create_index("ix_review_items_user_due", "review_items", ["user_id", "due_date"])
    op.add_column("agent_runs", sa.Column("prompt_tokens", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("agent_runs", sa.Column("completion_tokens", sa.Integer(), nullable=False, server_default="0"))


def downgrade() -> None:
    op.drop_column("agent_runs", "completion_tokens")
    op.drop_column("agent_runs", "prompt_tokens")
    op.drop_index("ix_review_items_user_due", table_name="review_items")
    op.drop_table("review_items")
