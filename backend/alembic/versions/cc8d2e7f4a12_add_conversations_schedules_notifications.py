"""add conversations, schedules, and notifications."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "cc8d2e7f4a12"
down_revision = "bb7f8c2d5e11"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("conversations", sa.Column("id", sa.String(32), primary_key=True), sa.Column("user_id", sa.String(32), nullable=False), sa.Column("title", sa.String(120), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"))
    op.create_index("ix_conversations_user_updated", "conversations", ["user_id", "updated_at"])
    op.create_table("conversation_messages", sa.Column("id", sa.String(32), primary_key=True), sa.Column("conversation_id", sa.String(32), nullable=False), sa.Column("role", sa.String(20), nullable=False), sa.Column("content", sa.Text(), nullable=False), sa.Column("tool_calls", sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="CASCADE"))
    op.create_index("ix_conversation_messages_conversation", "conversation_messages", ["conversation_id", "created_at"])
    op.create_table("agent_schedules", sa.Column("id", sa.String(32), primary_key=True), sa.Column("user_id", sa.String(32), nullable=False), sa.Column("type", sa.String(20), nullable=False), sa.Column("cron", sa.String(60), nullable=False), sa.Column("goal", sa.String(500), nullable=False), sa.Column("enabled", sa.Boolean(), nullable=False), sa.Column("last_run_at", sa.DateTime(timezone=True)), sa.Column("next_run_at", sa.DateTime(timezone=True)), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"))
    op.create_index("ix_agent_schedules_user_enabled", "agent_schedules", ["user_id", "enabled"])
    op.create_table("notifications", sa.Column("id", sa.String(32), primary_key=True), sa.Column("user_id", sa.String(32), nullable=False), sa.Column("type", sa.String(20), nullable=False), sa.Column("title", sa.String(120), nullable=False), sa.Column("content", sa.String(2000), nullable=False), sa.Column("action_url", sa.String(255)), sa.Column("read", sa.Boolean(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"))
    op.create_index("ix_notifications_user_created", "notifications", ["user_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_notifications_user_created", table_name="notifications"); op.drop_table("notifications")
    op.drop_index("ix_agent_schedules_user_enabled", table_name="agent_schedules"); op.drop_table("agent_schedules")
    op.drop_index("ix_conversation_messages_conversation", table_name="conversation_messages"); op.drop_table("conversation_messages")
    op.drop_index("ix_conversations_user_updated", table_name="conversations"); op.drop_table("conversations")
