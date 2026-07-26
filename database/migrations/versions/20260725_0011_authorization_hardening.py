"""authorization hardening — membership, policies, audits

Revision ID: 20260725_0011
Revises: 20260721_0010
Create Date: 2026-07-25 00:00:00
"""

from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import uuid4

import sqlalchemy as sa
from alembic import op

revision: str = "20260725_0011"
down_revision: str | None = "20260721_0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DEFAULT_WORKSPACE_ID = "00000000-0000-4000-8000-000000000001"


def upgrade() -> None:
    op.create_table(
        "workspace_memberships",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("workspace_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspace_workspaces.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "workspace_id",
            "user_id",
            name="uq_workspace_memberships_workspace_user",
        ),
    )
    op.create_index(
        "ix_workspace_memberships_workspace_id",
        "workspace_memberships",
        ["workspace_id"],
    )
    op.create_index(
        "ix_workspace_memberships_user_id",
        "workspace_memberships",
        ["user_id"],
    )

    # Existing users become members of the seeded Default Workspace.
    connection = op.get_bind()
    user_ids = connection.execute(sa.text("SELECT id FROM auth_users")).scalars().all()
    now = datetime.now(UTC)
    if user_ids:
        op.bulk_insert(
            sa.table(
                "workspace_memberships",
                sa.column("id", sa.String),
                sa.column("workspace_id", sa.String),
                sa.column("user_id", sa.String),
                sa.column("role", sa.String),
                sa.column("created_at", sa.DateTime(timezone=True)),
            ),
            [
                {
                    "id": str(uuid4()),
                    "workspace_id": DEFAULT_WORKSPACE_ID,
                    "user_id": user_id,
                    "role": "member",
                    "created_at": now,
                }
                for user_id in user_ids
            ],
        )

    op.create_table(
        "automation_capability_policies",
        sa.Column("workspace_id", sa.String(length=36), nullable=False),
        sa.Column("capability_id", sa.String(length=128), nullable=False),
        sa.Column("permission_mode", sa.String(length=32), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("workspace_id", "capability_id"),
    )

    op.create_table(
        "automation_execution_audits",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("execution_id", sa.String(length=36), nullable=False),
        sa.Column("workspace_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=True),
        sa.Column("capability_id", sa.String(length=128), nullable=False),
        sa.Column("operation", sa.String(length=128), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("permission_mode", sa.String(length=32), nullable=False),
        sa.Column("arguments", sa.JSON(), nullable=False),
        sa.Column("result_summary", sa.JSON(), nullable=False),
        sa.Column("duration", sa.Float(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("conversation_id", sa.String(length=36), nullable=True),
        sa.Column("correlation_id", sa.String(length=128), nullable=True),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_automation_execution_audits_execution_id",
        "automation_execution_audits",
        ["execution_id"],
    )
    op.create_index(
        "ix_automation_execution_audits_workspace_id",
        "automation_execution_audits",
        ["workspace_id"],
    )
    op.create_index(
        "ix_automation_execution_audits_user_id",
        "automation_execution_audits",
        ["user_id"],
    )
    op.create_index(
        "ix_automation_execution_audits_capability_id",
        "automation_execution_audits",
        ["capability_id"],
    )
    op.create_index(
        "ix_automation_execution_audits_timestamp",
        "automation_execution_audits",
        ["timestamp"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_automation_execution_audits_timestamp",
        table_name="automation_execution_audits",
    )
    op.drop_index(
        "ix_automation_execution_audits_capability_id",
        table_name="automation_execution_audits",
    )
    op.drop_index(
        "ix_automation_execution_audits_user_id",
        table_name="automation_execution_audits",
    )
    op.drop_index(
        "ix_automation_execution_audits_workspace_id",
        table_name="automation_execution_audits",
    )
    op.drop_index(
        "ix_automation_execution_audits_execution_id",
        table_name="automation_execution_audits",
    )
    op.drop_table("automation_execution_audits")
    op.drop_table("automation_capability_policies")
    op.drop_index("ix_workspace_memberships_user_id", table_name="workspace_memberships")
    op.drop_index("ix_workspace_memberships_workspace_id", table_name="workspace_memberships")
    op.drop_table("workspace_memberships")
