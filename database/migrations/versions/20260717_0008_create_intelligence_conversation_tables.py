"""create intelligence conversation tables

Revision ID: 20260717_0008
Revises: 20260717_0007
Create Date: 2026-07-17 15:40:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260717_0008"
down_revision: str | None = "20260717_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "intelligence_conversations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "intelligence_conversation_turns",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("conversation_id", sa.String(length=36), nullable=False),
        sa.Column("turn_index", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("citations", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["intelligence_conversations.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "conversation_id",
            "turn_index",
            name="uq_intelligence_conversation_turns_conversation_index",
        ),
    )
    op.create_index(
        "ix_intelligence_conversation_turns_conversation_id",
        "intelligence_conversation_turns",
        ["conversation_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_intelligence_conversation_turns_conversation_id",
        table_name="intelligence_conversation_turns",
    )
    op.drop_table("intelligence_conversation_turns")
    op.drop_table("intelligence_conversations")
