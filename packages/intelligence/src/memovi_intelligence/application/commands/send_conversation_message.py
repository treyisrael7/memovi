from collections.abc import Iterator
from dataclasses import dataclass

from memovi_shared import WorkspaceId

from memovi_intelligence.application.commands.reason import (
    Reason,
    ReasonStreamCompleted,
    ReasonStreamToken,
)
from memovi_intelligence.application.services.conversation_service import ConversationService
from memovi_intelligence.domain.entities import ReasoningRequest, ReasoningResult
from memovi_intelligence.domain.value_objects import (
    Citation,
    ConversationHistory,
    ConversationId,
    ConversationRole,
    ExecutionTrace,
)


@dataclass(frozen=True, slots=True)
class SendConversationMessageCommand:
    conversation_id: str
    workspace_id: WorkspaceId
    message: str
    provider: str | None = None
    model: str | None = None


@dataclass(frozen=True, slots=True)
class SendConversationMessageResult:
    conversation_id: str
    assistant_message: str
    citations: tuple[Citation, ...]
    provider: str
    model: str
    execution_trace: ExecutionTrace
    reasoning_result: ReasoningResult
    title: str | None = None


@dataclass(frozen=True, slots=True)
class SendMessageStreamToken:
    content: str


@dataclass(frozen=True, slots=True)
class SendMessageStreamCompleted:
    result: SendConversationMessageResult


class SendConversationMessage:
    """Send a user message through Reason and persist both turns."""

    def __init__(
        self,
        *,
        conversations: ConversationService,
        reason: Reason,
    ) -> None:
        self._conversations = conversations
        self._reason = reason

    def execute(
        self,
        command: SendConversationMessageCommand,
    ) -> SendConversationMessageResult:
        conversation_id = ConversationId(command.conversation_id)
        history = self._conversations.load_history(
            conversation_id,
            workspace_id=command.workspace_id,
        )

        result = self._reason.execute(
            ReasoningRequest.create(query=command.message),
            conversation_history=history,
            provider=command.provider,
            model=command.model,
        )

        updated = self._conversations.append_user_turn(
            conversation_id,
            command.message,
            workspace_id=command.workspace_id,
        )
        self._conversations.append_assistant_turn(
            conversation_id,
            result.answer,
            workspace_id=command.workspace_id,
            citations=result.citations,
        )

        return SendConversationMessageResult(
            conversation_id=conversation_id.value,
            assistant_message=result.answer,
            citations=result.citations,
            provider=result.provider,
            model=result.execution_trace.metrics.model,
            execution_trace=result.execution_trace,
            reasoning_result=result,
            title=updated.title,
        )

    def execute_stream(
        self,
        command: SendConversationMessageCommand,
    ) -> Iterator[SendMessageStreamToken | SendMessageStreamCompleted]:
        conversation_id = ConversationId(command.conversation_id)
        history = self._conversations.load_history(
            conversation_id,
            workspace_id=command.workspace_id,
        )

        already_recorded = (
            bool(history.turns)
            and history.turns[-1].role is ConversationRole.USER
            and history.turns[-1].content == command.message
        )
        if already_recorded:
            updated = self._conversations.get_conversation(
                conversation_id,
                workspace_id=command.workspace_id,
            )
            reason_history = ConversationHistory(
                turns=history.turns[:-1],
            )
        else:
            updated = self._conversations.append_user_turn(
                conversation_id,
                command.message,
                workspace_id=command.workspace_id,
            )
            reason_history = history

        final: ReasoningResult | None = None
        for event in self._reason.execute_stream(
            ReasoningRequest.create(query=command.message),
            conversation_history=reason_history,
            provider=command.provider,
            model=command.model,
        ):
            if isinstance(event, ReasonStreamToken):
                yield SendMessageStreamToken(content=event.content)
            elif isinstance(event, ReasonStreamCompleted):
                final = event.result

        if final is None:
            raise RuntimeError("Streaming reason completed without a final result.")

        self._conversations.append_assistant_turn(
            conversation_id,
            final.answer,
            workspace_id=command.workspace_id,
            citations=final.citations,
        )

        yield SendMessageStreamCompleted(
            result=SendConversationMessageResult(
                conversation_id=conversation_id.value,
                assistant_message=final.answer,
                citations=final.citations,
                provider=final.provider,
                model=final.execution_trace.metrics.model,
                execution_trace=final.execution_trace,
                reasoning_result=final,
                title=updated.title,
            )
        )
