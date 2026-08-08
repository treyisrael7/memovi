"""Request-scoped connector dependency wiring for the API composition root."""

from __future__ import annotations

from documents.application.commands.ingest_connector_document import IngestConnectorDocument
from documents.api.dependencies import get_object_storage
from documents.infrastructure.repositories import (
    SqlAlchemyDocumentRepository,
    SqlAlchemyProcessingJobRepository,
)
from fastapi import Request
from memovi_connectors.application.services import ConnectorScheduler
from memovi_connectors.application.services.filesystem_folder_service import FilesystemFolderService
from memovi_connectors.domain.value_objects import CONNECTOR_FILESYSTEM
from memovi_connectors.infrastructure.filesystem_connector import FilesystemConnector
from memovi_connectors.infrastructure.repositories.sqlalchemy_filesystem_folder_repository import (
    SqlAlchemyFilesystemFolderRepository,
)
from sqlalchemy.orm import Session as OrmSession

from api.document_import_port import DocumentsDocumentImportPort


def build_filesystem_folder_service(
    request: Request,
    session: OrmSession,
    scheduler: ConnectorScheduler,
) -> FilesystemFolderService:
    """Build a folder service and bind request-scoped Documents import."""
    folders = SqlAlchemyFilesystemFolderRepository(session)

    pending_jobs = getattr(request.state, "pending_processing_job_ids", None)
    if pending_jobs is None:
        pending_jobs = []
        request.state.pending_processing_job_ids = pending_jobs
    request.state.connector_pending_processing_job_ids = pending_jobs

    ingest = IngestConnectorDocument(
        documents=SqlAlchemyDocumentRepository(session),
        processing_jobs=SqlAlchemyProcessingJobRepository(session),
        object_storage=get_object_storage(),
    )
    document_import = DocumentsDocumentImportPort(
        ingest=ingest,
        on_processing_job=pending_jobs.append,
    )

    connector = getattr(request.app.state, "filesystem_connector", None)
    if isinstance(connector, FilesystemConnector):
        connector.configure_runtime(document_import=document_import, folders=folders)
    else:
        registry = request.app.state.connector_registry
        registered = registry.get(CONNECTOR_FILESYSTEM)
        if isinstance(registered, FilesystemConnector):
            registered.configure_runtime(document_import=document_import, folders=folders)

    return FilesystemFolderService(folders=folders, scheduler=scheduler)
