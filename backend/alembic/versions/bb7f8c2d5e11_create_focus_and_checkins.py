"""create focus sessions and daily checkins."""
from alembic import op
import sqlalchemy as sa

revision = "bb7f8c2d5e11"
down_revision = "aa6341f2fc83"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("focus_sessions",
        sa.Column("id", sa.String(32), primary_key=True), sa.Column("user_id", sa.String(32), nullable=False),
        sa.Column("goal_id", sa.String(32), nullable=False), sa.Column("planned_minutes", sa.Integer(), nullable=False),
        sa.Column("actual_minutes", sa.Integer(), nullable=False), sa.Column("mode", sa.String(20), nullable=False),
        sa.Column("completed", sa.Boolean(), nullable=False), sa.Column("note", sa.Text()),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.Column("ended_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"), sa.ForeignKeyConstraint(["goal_id"], ["goals.id"], ondelete="CASCADE"))
    op.create_index("ix_focus_goal", "focus_sessions", ["goal_id"])
    op.create_index("ix_focus_user_started", "focus_sessions", ["user_id", "started_at"])
    op.create_table("checkins",
        sa.Column("id", sa.String(32), primary_key=True), sa.Column("user_id", sa.String(32), nullable=False), sa.Column("goal_id", sa.String(32)),
        sa.Column("mood", sa.String(20)), sa.Column("content", sa.Text()), sa.Column("checkin_date", sa.Date(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"), sa.ForeignKeyConstraint(["goal_id"], ["goals.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("user_id", "checkin_date", name="uq_checkin_day"))
    op.create_index("ix_checkin_user_date", "checkins", ["user_id", "checkin_date"])


def downgrade() -> None:
    op.drop_index("ix_checkin_user_date", table_name="checkins"); op.drop_table("checkins")
    op.drop_index("ix_focus_user_started", table_name="focus_sessions"); op.drop_index("ix_focus_goal", table_name="focus_sessions"); op.drop_table("focus_sessions")
