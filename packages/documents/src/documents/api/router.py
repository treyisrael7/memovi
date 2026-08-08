from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from memovi_observability import timed_operation
from memovi_shared import WorkspaceId

from documents.api.dependencies import (
    get_active_workspace_id,
    get_delete_document,
    get_document_query,
    get_ingest_local_document,
    get_list_documents_query,
    get_reprocess_document,
)
from documents.api.schemas import (
    DocumentListResponse,
    DocumentResponse,
    IngestDocumentResponse,
    ReprocessDocumentResponse,
)
from documents.application.commands.delete_document import DeleteDocument, DeleteDocumentCommand
from documents.application.commands.ingest_local_document import (
    IngestLocalDocument,
    IngestLocalDocumentCommand,
)
from documents.application.commands.reprocess_document import (
    ReprocessDocument,
    ReprocessDocumentCommand,
)
from documents.application.dto import DocumentDto
from documents.application.exceptions import (
    DocumentNotFoundError,
    DocumentVersionNotFoundError,
    EmptyUploadError,
    UnsupportedMimeTypeError,
)
from documents.application.queries import GetDocument, ListDocuments
from documents.domain.exceptions import DocumentsDomainError

router = APIRouter(prefix="/documents", tags=["documents"])


def _to_response(document: DocumentDto) -> DocumentResponse:
    return DocumentResponse(
        id=document.id,
        name=document.name,
        mime_type=document.mime_type,
        source_type=document.source_type,
        created_at=document.created_at,
        processing_status=document.processing_status,
        processing_failure_reason=document.processing_failure_reason,
        processing_updated_at=document.processing_updated_at,
    )


@router.get(
    "",
    response_model=DocumentListResponse,
    status_code=status.HTTP_200_OK,
    summary="List source documents",
    description=(
        "List documents in the active workspace, including processing status. "
        "Active workspace is resolved from X-Memovi-Workspace-Id or the Default Workspace."
    ),
)
def list_documents(
    use_case: Annotated[ListDocuments, Depends(get_list_documents_query)],
    workspace_id: Annotated[WorkspaceId, Depends(get_active_workspace_id)],
) -> DocumentListResponse:
    documents = use_case.execute(workspace_id=workspace_id)
    return DocumentListResponse(items=[_to_response(document) for document in documents])


@router.get(
    "/{document_id}",
    response_model=DocumentResponse,
    status_code=status.HTTP_200_OK,
    summary="Get source document",
    responses={
        200: {"description": "Document detail."},
        404: {"description": "Document was not found in the active workspace."},
    },
)
def get_document(
    document_id: str,
    use_case: Annotated[GetDocument, Depends(get_document_query)],
    workspace_id: Annotated[WorkspaceId, Depends(get_active_workspace_id)],
) -> DocumentResponse:
    try:
        document = use_case.execute(document_id, workspace_id=workspace_id)
    except DocumentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    return _to_response(document)


@router.post(
    "",
    response_model=IngestDocumentResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def ingest_document(
    request: Request,
    file: Annotated[UploadFile, File()],
    use_case: Annotated[IngestLocalDocument, Depends(get_ingest_local_document)],
    workspace_id: Annotated[WorkspaceId, Depends(get_active_workspace_id)],
) -> IngestDocumentResponse:
    content = await file.read()
    filename = file.filename or "upload"
    mime_type = file.content_type or "application/octet-stream"

    try:
        with timed_operation(
            "document.upload",
            metric_name="memovi.documents.upload.latency",
            attributes={"operation": "document.upload"},
        ):
            result = use_case.execute(
                IngestLocalDocumentCommand(
                    workspace_id=workspace_id,
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

    request.state.pending_processing_job_ids.append(result.processing_job_id)
    request.state.pending_domain_events.append(result.event)

    return IngestDocumentResponse(
        document_id=result.document_id,
        processing_job_id=result.processing_job_id,
        processing_status=result.processing_status.value,
    )


@router.post(
    "/{document_id}/reprocess",
    response_model=ReprocessDocumentResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Reprocess a document",
    description="Re-run ingestion processing for a document's most recent stored version.",
    responses={
        202: {"description": "Reprocessing was queued."},
        404: {"description": "Document was not found in the active workspace."},
        409: {"description": "Document has no stored version to reprocess."},
    },
)
def reprocess_document(
    request: Request,
    document_id: str,
    use_case: Annotated[ReprocessDocument, Depends(get_reprocess_document)],
    workspace_id: Annotated[WorkspaceId, Depends(get_active_workspace_id)],
) -> ReprocessDocumentResponse:
    try:
        result = use_case.execute(
            ReprocessDocumentCommand(document_id=document_id, workspace_id=workspace_id),
        )
    except DocumentVersionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except (DocumentNotFoundError, DocumentsDomainError) as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document was not found.",
        ) from exc

    request.state.pending_processing_job_ids.append(result.processing_job_id)

    return ReprocessDocumentResponse(
        document_id=result.document_id,
        processing_job_id=result.processing_job_id,
        processing_status=result.processing_status.value,
    )


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a document",
    description="Permanently remove a document, its versions, and its stored artifact.",
    responses={
        204: {"description": "Document was deleted."},
        404: {"description": "Document was not found in the active workspace."},
    },
)
def delete_document(
    document_id: str,
    use_case: Annotated[DeleteDocument, Depends(get_delete_document)],
    workspace_id: Annotated[WorkspaceId, Depends(get_active_workspace_id)],
) -> None:
    try:
        use_case.execute(
            DeleteDocumentCommand(document_id=document_id, workspace_id=workspace_id),
        )
    except (DocumentNotFoundError, DocumentsDomainError) as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document was not found.",
        ) from exc
