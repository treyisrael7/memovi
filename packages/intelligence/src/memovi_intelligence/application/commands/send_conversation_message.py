from dataclasses import dataclass

from memovi_intelligence.application.commands.reason import Reason
from memovi_intelligence.application.services.conversation_service import ConversationService
from memovi_intelligence.domain.entities import ReasoningRequest, ReasoningResult
from memovi_intelligence.domain.value_objects import Citation, ConversationId, ExecutionTrace


@dataclass(frozen=True, slots=True)
class SendConversationMessageCommand:
    conversation_id: str
    message: str


@dataclass(frozen=True, slots=True)
class SendConversationMessageResult:
    conversation_id: str
    assistant_message: str
    citations: tuple[Citation, ...]
    provider: str
    model: str
    execution_trace: ExecutionTrace
    reasoning_result: ReasoningResult


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
        history = self._conversations.load_history(conversation_id)

        result = self._reason.execute(
            ReasoningRequest.create(query=command.message),
            conversation_history=history,
        )

        self._conversations.append_user_turn(conversation_id, command.message)
        self._conversations.append_assistant_turn(
            conversation_id,
            result.answer,
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
        )
