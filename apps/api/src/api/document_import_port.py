"""Composition-root DocumentImportPort adapter into Documents."""

from __future__ import annotations

from collections.abc import Callable

from documents.application.commands.ingest_connector_document import (
    IngestConnectorDocument,
    IngestConnectorDocumentCommand,
)
from documents.application.exceptions import EmptyUploadError, UnsupportedMimeTypeError
from memovi_connectors.domain.value_objects import NormalizedImportItem


class DocumentsDocumentImportPort:
    """Hands normalized connector items to Documents ingest/update/delete."""

    def __init__(
        self,
        *,
        ingest: IngestConnectorDocument,
        on_processing_job: Callable[[str], None] | None = None,
    ) -> None:
        self._ingest = ingest
        self._on_processing_job = on_processing_job

    def import_item(self, item: NormalizedImportItem) -> str:
        external_path = item.metadata.extra.get("external_path")
        path_text = external_path if isinstance(external_path, str) else item.metadata.source
        try:
            result = self._ingest.execute(
                IngestConnectorDocumentCommand(
                    workspace_id=item.metadata.workspace_id,
                    name=item.name,
                    mime_type=item.mime_type,
                    content=item.content,
                    connector_id=item.metadata.connector_id,
                    external_id=item.metadata.external_id,
                    external_path=path_text,
                    change_kind=item.change_kind,
                ),
            )
        except (EmptyUploadError, UnsupportedMimeTypeError):
            if item.change_kind == "upsert":
                raise
            return ""

        if result.processing_job_id and self._on_processing_job is not None:
            self._on_processing_job(result.processing_job_id)
        return result.document_id
