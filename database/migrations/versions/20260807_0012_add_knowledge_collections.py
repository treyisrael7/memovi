"""add knowledge collections tables

Revision ID: 20260807_0012
Revises: 20260725_0011
Create Date: 2026-08-07 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260807_0012"
down_revision: str | None = "20260725_0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "memory_collections",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("workspace_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=256), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_memory_collections_workspace_id",
        "memory_collections",
        ["workspace_id"],
    )

    op.create_table(
        "memory_collection_memberships",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("collection_id", sa.String(length=36), nullable=False),
        sa.Column("workspace_id", sa.String(length=36), nullable=False),
        sa.Column("member_kind", sa.String(length=32), nullable=False),
        sa.Column("member_id", sa.String(length=256), nullable=False),
        sa.Column("reason", sa.String(length=500), nullable=False),
        sa.Column("added_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["collection_id"],
            ["memory_collections.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "collection_id",
            "member_kind",
            "member_id",
            name="uq_memory_collection_memberships_item",
        ),
    )
    op.create_index(
        "ix_memory_collection_memberships_collection_id",
        "memory_collection_memberships",
        ["collection_id"],
    )
    op.create_index(
        "ix_memory_collection_memberships_workspace_id",
        "memory_collection_memberships",
        ["workspace_id"],
    )
    op.create_index(
        "ix_memory_collection_memberships_member_kind",
        "memory_collection_memberships",
        ["member_kind"],
    )
    op.create_index(
        "ix_memory_collection_memberships_member_id",
        "memory_collection_memberships",
        ["member_id"],
    )

    op.create_table(
        "memory_collection_activity",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("collection_id", sa.String(length=36), nullable=False),
        sa.Column("workspace_id", sa.String(length=36), nullable=False),
        sa.Column("activity_type", sa.String(length=64), nullable=False),
        sa.Column("member_kind", sa.String(length=32), nullable=True),
        sa.Column("member_id", sa.String(length=256), nullable=True),
        sa.Column("detail", sa.Text(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["collection_id"],
            ["memory_collections.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_memory_collection_activity_collection_id",
        "memory_collection_activity",
        ["collection_id"],
    )
    op.create_index(
        "ix_memory_collection_activity_workspace_id",
        "memory_collection_activity",
        ["workspace_id"],
    )
    op.create_index(
        "ix_memory_collection_activity_occurred_at",
        "memory_collection_activity",
        ["occurred_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_memory_collection_activity_occurred_at",
        table_name="memory_collection_activity",
    )
    op.drop_index(
        "ix_memory_collection_activity_workspace_id",
        table_name="memory_collection_activity",
    )
    op.drop_index(
        "ix_memory_collection_activity_collection_id",
        table_name="memory_collection_activity",
    )
    op.drop_table("memory_collection_activity")

    op.drop_index(
        "ix_memory_collection_memberships_member_id",
        table_name="memory_collection_memberships",
    )
    op.drop_index(
        "ix_memory_collection_memberships_member_kind",
        table_name="memory_collection_memberships",
    )
    op.drop_index(
        "ix_memory_collection_memberships_workspace_id",
        table_name="memory_collection_memberships",
    )
    op.drop_index(
        "ix_memory_collection_memberships_collection_id",
        table_name="memory_collection_memberships",
    )
    op.drop_table("memory_collection_memberships")

    op.drop_index("ix_memory_collections_workspace_id", table_name="memory_collections")
    op.drop_table("memory_collections")
