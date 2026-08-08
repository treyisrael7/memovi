"""add durable document processing queue columns

Revision ID: 20260808_0014
Revises: 20260808_0013
Create Date: 2026-08-08 18:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260808_0014"
down_revision: str | None = "20260808_0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "documents_processing_jobs",
        sa.Column("attempt", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column(
        "documents_processing_jobs",
        sa.Column("request_id", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "documents_processing_jobs",
        sa.Column("workspace_id", sa.String(length=36), nullable=True),
    )
    op.add_column(
        "documents_processing_jobs",
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "documents_processing_jobs",
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "documents_processing_jobs",
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "documents_processing_jobs",
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_documents_processing_jobs_status_available",
        "documents_processing_jobs",
        ["status", "available_at", "claimed_at", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_documents_processing_jobs_status_available",
        table_name="documents_processing_jobs",
    )
    op.drop_column("documents_processing_jobs", "claimed_at")
    op.drop_column("documents_processing_jobs", "available_at")
    op.drop_column("documents_processing_jobs", "completed_at")
    op.drop_column("documents_processing_jobs", "started_at")
    op.drop_column("documents_processing_jobs", "workspace_id")
    op.drop_column("documents_processing_jobs", "request_id")
    op.drop_column("documents_processing_jobs", "attempt")
