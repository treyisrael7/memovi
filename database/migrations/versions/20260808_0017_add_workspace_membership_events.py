"""add workspace membership audit events

Revision ID: 20260808_0017
Revises: 20260808_0016
Create Date: 2026-08-08 22:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260808_0017"
down_revision: str | None = "20260808_0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "workspace_membership_events",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("workspace_id", sa.String(length=36), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("actor_user_id", sa.String(length=36), nullable=False),
        sa.Column("target_user_id", sa.String(length=36), nullable=False),
        sa.Column("detail", sa.String(length=512), nullable=False, server_default=""),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspace_workspaces.id"],
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_workspace_membership_events_workspace_id",
        "workspace_membership_events",
        ["workspace_id"],
    )
    op.create_index(
        "ix_workspace_membership_events_event_type",
        "workspace_membership_events",
        ["event_type"],
    )
    op.create_index(
        "ix_workspace_membership_events_actor_user_id",
        "workspace_membership_events",
        ["actor_user_id"],
    )
    op.create_index(
        "ix_workspace_membership_events_target_user_id",
        "workspace_membership_events",
        ["target_user_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_workspace_membership_events_target_user_id",
        table_name="workspace_membership_events",
    )
    op.drop_index(
        "ix_workspace_membership_events_actor_user_id",
        table_name="workspace_membership_events",
    )
    op.drop_index(
        "ix_workspace_membership_events_event_type",
        table_name="workspace_membership_events",
    )
    op.drop_index(
        "ix_workspace_membership_events_workspace_id",
        table_name="workspace_membership_events",
    )
    op.drop_table("workspace_membership_events")
