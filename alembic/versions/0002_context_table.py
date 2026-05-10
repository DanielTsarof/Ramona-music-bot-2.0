"""context table

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-10
"""

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "context",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("channel_id", sa.BigInteger(), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("author_name", sa.String(100), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("tokens", sa.Integer(), nullable=True),
        sa.Column("model", sa.String(100), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id"),
    )
    op.create_index("ix_context_channel_id", "context", ["channel_id"])


def downgrade() -> None:
    op.drop_index("ix_context_channel_id", table_name="context")
    op.drop_table("context")
