"""add document connector provenance and filesystem folder connections

Revision ID: 20260808_0018
Revises: 20260808_0017
Create Date: 2026-08-08 23:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260808_0018"
down_revision: str | None = "20260808_0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "documents_documents",
        sa.Column("connector_id", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "documents_documents",
        sa.Column("external_id", sa.String(length=1024), nullable=True),
    )
    op.add_column(
        "documents_documents",
        sa.Column("external_path", sa.String(length=2048), nullable=True),
    )
    op.create_index(
        "ix_documents_documents_connector_id",
        "documents_documents",
        ["connector_id"],
    )
    op.create_index(
        "uq_documents_documents_connector_external",
        "documents_documents",
        ["workspace_id", "connector_id", "external_id"],
        unique=True,
        postgresql_where=sa.text("connector_id IS NOT NULL AND external_id IS NOT NULL"),
        sqlite_where=sa.text("connector_id IS NOT NULL AND external_id IS NOT NULL"),
    )

    op.create_table(
        "connectors_filesystem_folders",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("workspace_id", sa.String(length=36), nullable=False),
        sa.Column("root_path", sa.String(length=2048), nullable=False),
        sa.Column("display_name", sa.String(length=512), nullable=False),
        sa.Column("sync_cursor", sa.Text(), nullable=True),
        sa.Column("sync_status", sa.String(length=32), nullable=False, server_default="idle"),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("imported_document_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_synchronized_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_connectors_filesystem_folders_workspace_id",
        "connectors_filesystem_folders",
        ["workspace_id"],
    )
    op.create_index(
        "uq_connectors_filesystem_folders_workspace_root",
        "connectors_filesystem_folders",
        ["workspace_id", "root_path"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        "uq_connectors_filesystem_folders_workspace_root",
        table_name="connectors_filesystem_folders",
    )
    op.drop_index(
        "ix_connectors_filesystem_folders_workspace_id",
        table_name="connectors_filesystem_folders",
    )
    op.drop_table("connectors_filesystem_folders")

    op.drop_index(
        "uq_documents_documents_connector_external",
        table_name="documents_documents",
    )
    op.drop_index("ix_documents_documents_connector_id", table_name="documents_documents")
    op.drop_column("documents_documents", "external_path")
    op.drop_column("documents_documents", "external_id")
    op.drop_column("documents_documents", "connector_id")
