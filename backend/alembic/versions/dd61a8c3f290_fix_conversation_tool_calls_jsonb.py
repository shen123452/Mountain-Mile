"""Store conversation tool calls as JSONB, matching the model."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "dd61a8c3f290"
down_revision = "cc8d2e7f4a12"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("conversation_messages", "tool_calls", type_=postgresql.JSONB(),
                    existing_type=postgresql.JSON(), postgresql_using="tool_calls::jsonb")


def downgrade() -> None:
    op.alter_column("conversation_messages", "tool_calls", type_=postgresql.JSON(),
                    existing_type=postgresql.JSONB(), postgresql_using="tool_calls::json")
