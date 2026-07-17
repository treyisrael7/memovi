from typing import Protocol

from memovi_intelligence.domain.entities import Conversation, ReasoningRequest, ReasoningResult
from memovi_intelligence.domain.value_objects import (
    ConversationId,
    ConversationTurn,
    Prompt,
    RetrievedKnowledge,
    ToolDefinition,
)


class KnowledgeRetriever(Protocol):
    """Retrieves ranked knowledge for reasoning without coupling to Search internals."""

    def retrieve(
        self,
        request: ReasoningRequest,
        *,
        limit: int,
    ) -> tuple[RetrievedKnowledge, ...]:
        raise NotImplementedError


class ReasoningProvider(Protocol):
    """Produces reasoning output from a provider-agnostic prompt."""

    def reason(self, prompt: Prompt) -> ReasoningResult:
        raise NotImplementedError


class ConversationRepository(Protocol):
    """Persistence contract for multi-turn conversation state."""

    def create(self) -> Conversation:
        raise NotImplementedError

    def get(self, conversation_id: ConversationId) -> Conversation | None:
        raise NotImplementedError

    def append_turn(
        self,
        conversation_id: ConversationId,
        turn: ConversationTurn,
    ) -> Conversation:
        raise NotImplementedError

    def list_turns(self, conversation_id: ConversationId) -> tuple[ConversationTurn, ...]:
        raise NotImplementedError


class Tool(Protocol):
    """Executable capability that can be discovered and invoked by Intelligence."""

    def name(self) -> str:
        raise NotImplementedError

    def description(self) -> str:
        raise NotImplementedError

    def schema(self) -> ToolDefinition:
        raise NotImplementedError

    def execute(self, arguments: dict[str, object]) -> object:
        raise NotImplementedError
