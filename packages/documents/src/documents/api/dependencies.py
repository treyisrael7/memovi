from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session as OrmSession

from documents.application.commands import (
    CompleteProcessing,
    CreateDocument,
    EnqueueDocumentProcessing,
    FailProcessing,
    IngestLocalDocument,
    ProcessDocument,
    StartProcessing,
)
from documents.application.ports import ObjectStorage, ProcessingJobQueue
from documents.application.queries import GetDocument, ListDocuments
from documents.infrastructure.events.noop_event_publisher import NoOpEventPublisher
from documents.infrastructure.processors import DefaultProcessorRegistry
from documents.infrastructure.repositories import (
    SqlAlchemyDocumentRepository,
    SqlAlchemyProcessingJobRepository,
)
from documents.infrastructure.storage import MinioObjectStorage


def get_database_session() -> OrmSession:
    raise RuntimeError("Documents database session dependency was not configured.")


DatabaseSession = Annotated[OrmSession, Depends(get_database_session)]


def get_processing_job_queue(request: Request) -> ProcessingJobQueue:
    queue = getattr(request.app.state, "processing_job_queue", None)
    if queue is None:
        raise RuntimeError("Processing job queue was not configured.")
    return queue


ProcessingJobQueueDependency = Annotated[ProcessingJobQueue, Depends(get_processing_job_queue)]


def get_object_storage() -> ObjectStorage:
    return MinioObjectStorage.from_env()


ObjectStorageDependency = Annotated[ObjectStorage, Depends(get_object_storage)]


def get_ingest_local_document(
    session: DatabaseSession,
    object_storage: ObjectStorageDependency,
) -> IngestLocalDocument:
    return IngestLocalDocument(
        documents=SqlAlchemyDocumentRepository(session),
        processing_jobs=SqlAlchemyProcessingJobRepository(session),
        object_storage=object_storage,
    )


def get_enqueue_document_processing(
    processing_job_queue: ProcessingJobQueueDependency,
) -> EnqueueDocumentProcessing:
    return EnqueueDocumentProcessing(processing_job_queue=processing_job_queue)


def get_create_document(session: DatabaseSession) -> CreateDocument:
    return CreateDocument(
        documents=SqlAlchemyDocumentRepository(session),
        processing_jobs=SqlAlchemyProcessingJobRepository(session),
    )


def get_start_processing(session: DatabaseSession) -> StartProcessing:
    return StartProcessing(
        processing_jobs=SqlAlchemyProcessingJobRepository(session),
    )


def get_complete_processing(session: DatabaseSession) -> CompleteProcessing:
    return CompleteProcessing(
        processing_jobs=SqlAlchemyProcessingJobRepository(session),
    )


def get_fail_processing(session: DatabaseSession) -> FailProcessing:
    return FailProcessing(
        processing_jobs=SqlAlchemyProcessingJobRepository(session),
    )


def get_document_query(session: DatabaseSession) -> GetDocument:
    return GetDocument(
        documents=SqlAlchemyDocumentRepository(session),
    )


def get_list_documents_query(session: DatabaseSession) -> ListDocuments:
    return ListDocuments(
        documents=SqlAlchemyDocumentRepository(session),
    )


def get_process_document(
    session: DatabaseSession,
    object_storage: ObjectStorageDependency,
) -> ProcessDocument:
    return ProcessDocument(
        documents=SqlAlchemyDocumentRepository(session),
        processing_jobs=SqlAlchemyProcessingJobRepository(session),
        object_storage=object_storage,
        processor_registry=DefaultProcessorRegistry(),
        event_publisher=NoOpEventPublisher(),
    )
