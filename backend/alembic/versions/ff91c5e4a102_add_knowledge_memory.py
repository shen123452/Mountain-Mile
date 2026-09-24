"""Add user memories and knowledge documents."""
from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

revision = "ff91c5e4a102"
down_revision = "ee74b2a160de"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("user_memories",
        sa.Column("id", sa.String(32), primary_key=True), sa.Column("user_id", sa.String(32), nullable=False),
        sa.Column("memory_type", sa.String(20), nullable=False, server_default="fact"), sa.Column("content", sa.Text(), nullable=False),
        sa.Column("importance", sa.Float(), nullable=False, server_default="0.5"), sa.Column("confidence", sa.Float(), nullable=False, server_default="0.7"),
        sa.Column("embedding", sa.JSON().with_variant(Vector(1024), "postgresql"), nullable=True), sa.Column("source", sa.String(40)), sa.Column("use_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_used", sa.DateTime(timezone=True)), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"))
    op.create_index("ix_user_memories_user_updated", "user_memories", ["user_id", "updated_at"])
    op.create_table("knowledge_docs",
        sa.Column("id", sa.String(32), primary_key=True), sa.Column("user_id", sa.String(32), nullable=False), sa.Column("title", sa.String(200), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False), sa.Column("mime_type", sa.String(120), nullable=False), sa.Column("object_key", sa.String(500)),
        sa.Column("source_url", sa.String(1000)), sa.Column("raw_data", sa.LargeBinary()), sa.Column("status", sa.String(20), nullable=False, server_default="ready"), sa.Column("char_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error", sa.Text()), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"))
    op.create_index("ix_knowledge_docs_user_created", "knowledge_docs", ["user_id", "created_at"])
    op.create_table("document_chunks",
        sa.Column("id", sa.String(32), primary_key=True), sa.Column("document_id", sa.String(32), nullable=False), sa.Column("user_id", sa.String(32), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False), sa.Column("content", sa.Text(), nullable=False), sa.Column("embedding", sa.JSON().with_variant(Vector(1024), "postgresql")), sa.Column("token_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["knowledge_docs.id"], ondelete="CASCADE"), sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"))
    op.create_index("ix_document_chunks_doc_index", "document_chunks", ["document_id", "chunk_index"])
    op.create_index("ix_document_chunks_user", "document_chunks", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_document_chunks_user", table_name="document_chunks"); op.drop_index("ix_document_chunks_doc_index", table_name="document_chunks"); op.drop_table("document_chunks")
    op.drop_index("ix_knowledge_docs_user_created", table_name="knowledge_docs"); op.drop_table("knowledge_docs")
    op.drop_index("ix_user_memories_user_updated", table_name="user_memories"); op.drop_table("user_memories")
