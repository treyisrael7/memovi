from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session as OrmSession

from documents.application.commands import (
    CompleteProcessing,
    CreateDocument,
    FailProcessing,
    StartProcessing,
)
from documents.application.queries import GetDocument, ListDocuments


def get_database_session() -> OrmSession:
    raise RuntimeError("Documents database session dependency was not configured.")


DatabaseSession = Annotated[OrmSession, Depends(get_database_session)]


def get_create_document(_session: DatabaseSession) -> CreateDocument:
    raise RuntimeError("CreateDocument dependency was not configured.")


def get_start_processing(_session: DatabaseSession) -> StartProcessing:
    raise RuntimeError("StartProcessing dependency was not configured.")


def get_complete_processing(_session: DatabaseSession) -> CompleteProcessing:
    raise RuntimeError("CompleteProcessing dependency was not configured.")


def get_fail_processing(_session: DatabaseSession) -> FailProcessing:
    raise RuntimeError("FailProcessing dependency was not configured.")


def get_document_query(_session: DatabaseSession) -> GetDocument:
    raise RuntimeError("GetDocument dependency was not configured.")


def get_list_documents_query(_session: DatabaseSession) -> ListDocuments:
    raise RuntimeError("ListDocuments dependency was not configured.")
