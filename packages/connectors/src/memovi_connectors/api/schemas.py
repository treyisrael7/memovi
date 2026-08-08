"""HTTP schemas for the Connector Framework API."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ConnectorMetadataResponse(BaseModel):
    connector_id: str
    display_name: str
    description: str
    source_category: str
    auth_methods: list[str]
    supports_incremental_sync: bool
    supports_delete_detection: bool


class ConnectorListResponse(BaseModel):
    items: list[ConnectorMetadataResponse]
    count: int


class ConnectorHealthResponse(BaseModel):
    connector_id: str
    status: str
    last_synchronized_at: datetime | None = None
    imported_document_count: int = 0
    pending_changes: int = 0
    errors: list[str] = Field(default_factory=list)
    message: str | None = None


class ConnectorHealthListResponse(BaseModel):
    items: list[ConnectorHealthResponse]
    count: int


class AddFilesystemFolderRequest(BaseModel):
    root_path: str = Field(min_length=1, max_length=2048)
    display_name: str | None = Field(default=None, max_length=512)


class FilesystemFolderResponse(BaseModel):
    id: str
    workspace_id: str
    root_path: str
    display_name: str
    sync_status: str
    last_error: str | None = None
    imported_document_count: int
    last_synchronized_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class FilesystemFolderListResponse(BaseModel):
    items: list[FilesystemFolderResponse]
    count: int


class SyncFilesystemFolderRequest(BaseModel):
    sync_mode: str | None = Field(default=None, pattern="^(initial|incremental)$")


class SyncFilesystemFolderResponse(BaseModel):
    folder: FilesystemFolderResponse
    success: bool
    sync_mode: str
    imported_count: int
    updated_count: int
    deleted_count: int
    skipped_count: int
    error_code: str | None = None
    error_message: str | None = None
