from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from documents.api.dependencies import get_ingest_local_document
from documents.api.schemas import IngestDocumentResponse
from documents.application.commands.ingest_local_document import (
    IngestLocalDocument,
    IngestLocalDocumentCommand,
)
from documents.application.exceptions import EmptyUploadError, UnsupportedMimeTypeError
from documents.domain.exceptions import DocumentsDomainError

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post(
    "",
    response_model=IngestDocumentResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def ingest_document(
    file: Annotated[UploadFile, File()],
    use_case: Annotated[IngestLocalDocument, Depends(get_ingest_local_document)],
) -> IngestDocumentResponse:
    content = await file.read()
    filename = file.filename or "upload"
    mime_type = file.content_type or "application/octet-stream"

    try:
        result = use_case.execute(
            IngestLocalDocumentCommand(
                filename=filename,
                mime_type=mime_type,
                content=content,
            ),
        )
    except EmptyUploadError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except UnsupportedMimeTypeError as exc:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=str(exc),
        ) from exc
    except DocumentsDomainError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    return IngestDocumentResponse(
        document_id=result.document_id,
        processing_job_id=result.processing_job_id,
        processing_status=result.processing_status.value,
    )
