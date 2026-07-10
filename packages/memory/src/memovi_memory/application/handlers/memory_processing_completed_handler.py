from collections.abc import Callable
from datetime import UTC, datetime

from sqlalchemy.orm import Session as OrmSession

from memovi_memory.application.commands.materialize_knowledge import (
    MaterializeKnowledge,
    MaterializeKnowledgeCommand,
)
from memovi_memory.application.dto.processing_completed_notification import (
    ProcessingCompletedNotification,
)
from memovi_memory.application.ports import EventPublisher, ProcessedDocumentReader
from memovi_memory.domain.events import KnowledgeMaterialized


class MemoryProcessingCompletedHandler:
    """Materializes knowledge when document processing completes successfully."""

    def __init__(
        self,
        *,
        processed_document_reader: ProcessedDocumentReader,
        materialize_knowledge_factory: Callable[[OrmSession], MaterializeKnowledge],
        event_publisher: EventPublisher,
        session_factory: Callable[[], OrmSession],
    ) -> None:
        self._processed_document_reader = processed_document_reader
        self._materialize_knowledge_factory = materialize_knowledge_factory
        self._event_publisher = event_publisher
        self._session_factory = session_factory

    def handle(self, notification: ProcessingCompletedNotification) -> None:
        snapshot = self._processed_document_reader.load_by_processing_job(
            notification.processing_job_id,
        )
        if snapshot is None:
            return

        normalized_content = snapshot.normalized_content
        if normalized_content is None or not normalized_content.strip():
            return

        session = self._session_factory()
        try:
            result = self._materialize_knowledge_factory(session).execute(
                MaterializeKnowledgeCommand(
                    document_id=snapshot.document_id,
                    document_version_id=snapshot.document_version_id,
                    normalized_text=normalized_content,
                ),
            )
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

        self._event_publisher.publish(
            KnowledgeMaterialized(
                knowledge_item_id=result.knowledge_item_id,
                document_id=snapshot.document_id,
                document_version_id=snapshot.document_version_id,
                chunk_count=result.chunk_count,
                occurred_at=datetime.now(UTC),
            ),
        )
