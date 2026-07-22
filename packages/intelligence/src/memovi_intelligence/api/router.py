from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from memovi_observability import DiagnosticEventEmitter, DiagnosticEventName, timed_operation
from memovi_shared import WorkspaceId

from memovi_intelligence.api.dependencies import (
    get_active_workspace_id,
    get_conversation_service,
    get_model_gateway,
    get_send_conversation_message,
)
from memovi_intelligence.api.schemas import (
    AvailableModelResponse,
    AvailableModelsResponse,
    CitationResponse,
    ConversationListResponse,
    ConversationMessageResponse,
    ConversationMessagesResponse,
    ConversationMetadataResponse,
    ConversationSummaryResponse,
    CreateConversationResponse,
    ExecutionMetadataResponse,
    ExecutionMetricsResponse,
    RenameConversationRequest,
    SendMessageRequest,
    SendMessageResponse,
    StageTimingResponse,
)
from memovi_intelligence.application.commands import (
    SendConversationMessage,
    SendConversationMessageCommand,
)
from memovi_intelligence.application.commands.send_conversation_message import (
    SendMessageStreamCompleted,
    SendMessageStreamToken,
)
from memovi_intelligence.application.services import ConversationService, ModelGateway
from memovi_intelligence.domain.exceptions import (
    ConversationNotFoundError,
    IntelligenceDomainError,
    InvalidConversationError,
    InvalidConversationIdError,
    InvalidReasoningQueryError,
    NoRetrievedKnowledgeError,
    ReasoningProviderError,
    ReasoningProviderTimeoutError,
    ReasoningProviderUnavailableError,
    UnknownReasoningProviderError,
)
from memovi_intelligence.domain.value_objects import Citation, ConversationId, ConversationTurn
from memovi_intelligence.domain.value_objects.execution_trace import ExecutionTrace

router = APIRouter(prefix="/conversations", tags=["conversations"])
_DIAGNOSTICS = DiagnosticEventEmitter()


def _citation_response(citation: Citation) -> CitationResponse:
    return CitationResponse(
        document_id=citation.document_id,
        chunk_id=citation.chunk_id,
        document_title=citation.document_title,
        score=citation.score,
    )


def _message_response(turn: ConversationTurn) -> ConversationMessageResponse:
    return ConversationMessageResponse(
        role=turn.role.value,
        content=turn.content,
        timestamp=turn.timestamp,
        citations=[_citation_response(citation) for citation in turn.citations],
    )


def _execution_response(
    *,
    execution_trace: ExecutionTrace,
    metadata: dict[str, Any],
) -> ExecutionMetadataResponse:
    metrics = execution_trace.metrics
    return ExecutionMetadataResponse(
        execution_time=execution_trace.total_duration,
        stages=[
            StageTimingResponse(
                stage=timing.stage.value,
                started_at=timing.started_at,
                finished_at=timing.finished_at,
                duration=timing.duration,
            )
            for timing in execution_trace.stages
        ],
        metrics=ExecutionMetricsResponse(
            provider=metrics.provider,
            model=metrics.model,
            estimated_input_tokens=metrics.estimated_input_tokens,
            output_tokens=metrics.output_tokens,
            retrieved_knowledge_count=metrics.retrieved_knowledge_count,
            document_count=metrics.document_count,
            citation_count=metrics.citation_count,
        ),
        metadata=metadata,
    )


def _send_message_response(result: Any) -> SendMessageResponse:
    return SendMessageResponse(
        conversation_id=result.conversation_id,
        assistant_message=result.assistant_message,
        citations=[_citation_response(citation) for citation in result.citations],
        provider=result.provider,
        model=result.model,
        title=result.title,
        execution=_execution_response(
            execution_trace=result.execution_trace,
            metadata=dict(result.reasoning_result.metadata),
        ),
    )


def _parse_conversation_id(conversation_id: str) -> ConversationId:
    try:
        return ConversationId(conversation_id)
    except InvalidConversationIdError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc


def _sse(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n"


def _map_send_errors(exc: Exception) -> HTTPException:
    if isinstance(exc, ConversationNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(exc, (InvalidConversationIdError, InvalidConversationError)):
        return HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        )
    if isinstance(exc, (InvalidReasoningQueryError, NoRetrievedKnowledgeError)):
        return HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        )
    if isinstance(exc, (UnknownReasoningProviderError, ReasoningProviderUnavailableError)):
        return HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        )
    if isinstance(exc, ReasoningProviderTimeoutError):
        return HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail=str(exc))
    if isinstance(exc, ReasoningProviderError):
        return HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))
    if isinstance(exc, IntelligenceDomainError):
        return HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        )
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Conversation request failed.",
    )


@router.get(
    "/models",
    response_model=AvailableModelsResponse,
    status_code=status.HTTP_200_OK,
    summary="List available reasoning models",
)
def list_models(
    gateway: Annotated[ModelGateway, Depends(get_model_gateway)],
) -> AvailableModelsResponse:
    models = [
        AvailableModelResponse(
            provider=provider,
            model=model,
            label=f"{provider}/{model}",
        )
        for provider, model in gateway.available_models()
    ]
    return AvailableModelsResponse(
        default_provider=gateway.provider_name,
        default_model=gateway.model,
        models=models,
    )


@router.post(
    "",
    response_model=CreateConversationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a conversation",
)
def create_conversation(
    conversations: Annotated[ConversationService, Depends(get_conversation_service)],
    workspace_id: Annotated[WorkspaceId, Depends(get_active_workspace_id)],
) -> CreateConversationResponse:
    with timed_operation(
        "conversation.create",
        attributes={"operation": "conversation.create"},
    ):
        conversation = conversations.create_conversation(workspace_id=workspace_id)
    _DIAGNOSTICS.emit(
        DiagnosticEventName.CONVERSATION_CREATED,
        conversation_id=conversation.id.value,
        workspace_id=workspace_id.value,
    )
    return CreateConversationResponse(
        conversation_id=conversation.id.value,
        title=conversation.title,
        created_at=conversation.created_at,
    )


@router.get(
    "",
    response_model=ConversationListResponse,
    status_code=status.HTTP_200_OK,
    summary="List conversations",
)
def list_conversations(
    conversations: Annotated[ConversationService, Depends(get_conversation_service)],
    workspace_id: Annotated[WorkspaceId, Depends(get_active_workspace_id)],
) -> ConversationListResponse:
    items = conversations.list_conversations(workspace_id=workspace_id)
    return ConversationListResponse(
        conversations=[
            ConversationSummaryResponse(
                conversation_id=item.id.value,
                title=item.title,
                created_at=item.created_at,
                updated_at=item.updated_at,
                message_count=len(item.turns),
            )
            for item in items
        ]
    )


@router.get(
    "/{conversation_id}",
    response_model=ConversationMetadataResponse,
    status_code=status.HTTP_200_OK,
    summary="Get conversation metadata",
)
def get_conversation(
    conversation_id: str,
    conversations: Annotated[ConversationService, Depends(get_conversation_service)],
    workspace_id: Annotated[WorkspaceId, Depends(get_active_workspace_id)],
) -> ConversationMetadataResponse:
    parsed_id = _parse_conversation_id(conversation_id)
    try:
        conversation = conversations.get_conversation(parsed_id, workspace_id=workspace_id)
    except ConversationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return ConversationMetadataResponse(
        conversation_id=conversation.id.value,
        title=conversation.title,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        message_count=len(conversation.turns),
    )


@router.patch(
    "/{conversation_id}",
    response_model=ConversationMetadataResponse,
    status_code=status.HTTP_200_OK,
    summary="Rename a conversation",
)
def rename_conversation(
    conversation_id: str,
    body: RenameConversationRequest,
    conversations: Annotated[ConversationService, Depends(get_conversation_service)],
    workspace_id: Annotated[WorkspaceId, Depends(get_active_workspace_id)],
) -> ConversationMetadataResponse:
    parsed_id = _parse_conversation_id(conversation_id)
    try:
        conversation = conversations.rename_conversation(
            parsed_id,
            body.title,
            workspace_id=workspace_id,
        )
    except ConversationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except InvalidConversationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc

    return ConversationMetadataResponse(
        conversation_id=conversation.id.value,
        title=conversation.title,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        message_count=len(conversation.turns),
    )


@router.delete(
    "/{conversation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a conversation",
)
def delete_conversation(
    conversation_id: str,
    conversations: Annotated[ConversationService, Depends(get_conversation_service)],
    workspace_id: Annotated[WorkspaceId, Depends(get_active_workspace_id)],
) -> None:
    parsed_id = _parse_conversation_id(conversation_id)
    try:
        conversations.delete_conversation(parsed_id, workspace_id=workspace_id)
    except ConversationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.get(
    "/{conversation_id}/messages",
    response_model=ConversationMessagesResponse,
    status_code=status.HTTP_200_OK,
    summary="List conversation messages",
)
def list_messages(
    conversation_id: str,
    conversations: Annotated[ConversationService, Depends(get_conversation_service)],
    workspace_id: Annotated[WorkspaceId, Depends(get_active_workspace_id)],
) -> ConversationMessagesResponse:
    parsed_id = _parse_conversation_id(conversation_id)
    try:
        conversation = conversations.get_conversation(parsed_id, workspace_id=workspace_id)
    except ConversationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return ConversationMessagesResponse(
        conversation_id=conversation.id.value,
        messages=[_message_response(turn) for turn in conversation.turns],
    )


@router.post(
    "/{conversation_id}/messages",
    response_model=SendMessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Send a conversation message",
    description=(
        "Append a user message, run the Reason pipeline "
        "(retrieve → assemble → prompt → model), persist the assistant turn, "
        "and return the assistant response with citations and execution metadata."
    ),
)
def send_message(
    conversation_id: str,
    body: SendMessageRequest,
    use_case: Annotated[SendConversationMessage, Depends(get_send_conversation_message)],
    workspace_id: Annotated[WorkspaceId, Depends(get_active_workspace_id)],
) -> SendMessageResponse:
    _parse_conversation_id(conversation_id)

    try:
        result = use_case.execute(
            SendConversationMessageCommand(
                conversation_id=conversation_id,
                workspace_id=workspace_id,
                message=body.message,
                provider=body.provider,
                model=body.model,
            ),
        )
    except Exception as exc:
        raise _map_send_errors(exc) from exc

    return _send_message_response(result)


@router.post(
    "/{conversation_id}/messages/stream",
    status_code=status.HTTP_200_OK,
    summary="Send a conversation message with token streaming",
    description=(
        "Server-Sent Events stream of assistant tokens followed by a terminal "
        "`done` event containing the persisted response metadata."
    ),
)
def stream_message(
    conversation_id: str,
    body: SendMessageRequest,
    use_case: Annotated[SendConversationMessage, Depends(get_send_conversation_message)],
    workspace_id: Annotated[WorkspaceId, Depends(get_active_workspace_id)],
) -> StreamingResponse:
    _parse_conversation_id(conversation_id)
    command = SendConversationMessageCommand(
        conversation_id=conversation_id,
        workspace_id=workspace_id,
        message=body.message,
        provider=body.provider,
        model=body.model,
    )

    def generate() -> Iterator[str]:
        try:
            for event in use_case.execute_stream(command):
                if isinstance(event, SendMessageStreamToken):
                    yield _sse("token", {"content": event.content})
                elif isinstance(event, SendMessageStreamCompleted):
                    payload = _send_message_response(event.result).model_dump(mode="json")
                    yield _sse("done", payload)
        except Exception as exc:
            mapped = _map_send_errors(exc)
            yield _sse(
                "error",
                {
                    "detail": mapped.detail,
                    "status": mapped.status_code,
                },
            )

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
