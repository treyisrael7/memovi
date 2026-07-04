from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session as OrmSession

from documents.application.commands import (
    CompleteProcessing,
    CreateDocument,
    FailProcessing,
    IngestLocalDocument,
    StartProcessing,
)
from documents.application.ports import ObjectStorage
from documents.application.queries import GetDocument, ListDocuments
from documents.infrastructure.repositories import (
    SqlAlchemyDocumentRepository,
    SqlAlchemyProcessingJobRepository,
)
from documents.infrastructure.storage import MinioObjectStorage


def get_database_session() -> OrmSession:
    raise RuntimeError("Documents database session dependency was not configured.")


DatabaseSession = Annotated[OrmSession, Depends(get_database_session)]


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
