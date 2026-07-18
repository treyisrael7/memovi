from collections.abc import Callable

from documents.domain.events import ProcessingCompleted
from documents.domain.value_objects import DocumentId
from documents.infrastructure.repositories import (
    SqlAlchemyDocumentRepository,
    SqlAlchemyProcessingJobRepository,
)
from memovi_memory.application.commands.materialize_knowledge import MaterializeKnowledge
from memovi_memory.application.dto.processed_document_snapshot import ProcessedDocumentSnapshot
from memovi_memory.application.dto.processing_completed_notification import (
    ProcessingCompletedNotification,
)
from memovi_memory.application.handlers import MemoryProcessingCompletedHandler
from memovi_memory.domain.services import ChunkGenerator, KnowledgeMaterializer
from memovi_memory.infrastructure.repositories import (
    SqlAlchemyChunkRepository,
    SqlAlchemyKnowledgeRepository,
)
from sqlalchemy.orm import Session as OrmSession

from api.events import InProcessEventDispatcher
from api.observability_bridge import register_observability_event_bridge
from api.search_integration import register_search_event_handlers


class SqlAlchemyProcessedDocumentReader:
    """Loads processed document content through the documents persistence layer."""

    def __init__(self, session_factory: Callable[[], OrmSession]) -> None:
        self._session_factory = session_factory

    def load_by_processing_job(
        self,
        processing_job_id: str,
    ) -> ProcessedDocumentSnapshot | None:
        session = self._session_factory()
        try:
            job = SqlAlchemyProcessingJobRepository(session).get_by_id(processing_job_id)
            if job is None:
                return None

            documents = SqlAlchemyDocumentRepository(session)
            version = documents.get_version_by_id(job.document_version_id)
            if version is None:
                return None

            document = documents.get_by_id_unscoped(DocumentId(job.document_id.value))
            if document is None:
                return None

            return ProcessedDocumentSnapshot(
                document_id=job.document_id.value,
                document_version_id=job.document_version_id,
                workspace_id=document.workspace_id.value,
                source_type=document.source_type.value,
                mime_type=document.mime_type.value,
                normalized_content=version.normalized_content,
            )
        finally:
            session.close()


def build_materialize_knowledge(session: OrmSession) -> MaterializeKnowledge:
    return MaterializeKnowledge(
        chunk_generator=ChunkGenerator(max_chunk_size=500),
        knowledge_materializer=KnowledgeMaterializer(),
        knowledge_repository=SqlAlchemyKnowledgeRepository(session),
        chunk_repository=SqlAlchemyChunkRepository(session),
    )


def register_memory_event_handlers(
    dispatcher: InProcessEventDispatcher,
    *,
    session_factory: Callable[[], OrmSession],
) -> MemoryProcessingCompletedHandler:
    handler = MemoryProcessingCompletedHandler(
        processed_document_reader=SqlAlchemyProcessedDocumentReader(session_factory),
        materialize_knowledge_factory=build_materialize_knowledge,
        event_publisher=dispatcher,
        session_factory=session_factory,
    )

    def on_processing_completed(event: object) -> None:
        if not isinstance(event, ProcessingCompleted):
            return

        handler.handle(
            ProcessingCompletedNotification(
                document_id=event.document_id.value,
                processing_job_id=event.processing_job_id,
                occurred_at=event.occurred_at,
            ),
        )

    dispatcher.subscribe(ProcessingCompleted, on_processing_completed)
    return handler


def configure_event_dispatch(
    *,
    session_factory: Callable[[], OrmSession],
) -> InProcessEventDispatcher:
    dispatcher = InProcessEventDispatcher()
    register_memory_event_handlers(dispatcher, session_factory=session_factory)
    register_search_event_handlers(dispatcher, session_factory=session_factory)
    register_observability_event_bridge(dispatcher)
    return dispatcher
