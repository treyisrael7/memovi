from typing import Protocol

from memovi_shared import WorkspaceId

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

    def reason(self, prompt: Prompt, *, model: str | None = None) -> ReasoningResult:
        raise NotImplementedError


class StreamingReasoningProvider(Protocol):
    """Optional streaming extension for providers that can emit token deltas."""

    def reason_stream(self, prompt: Prompt, *, model: str | None = None):
        """Yield content deltas for a prompt."""
        raise NotImplementedError


class ConversationRepository(Protocol):
    """Persistence contract for multi-turn conversation state."""

    def create(self, *, workspace_id: WorkspaceId) -> Conversation:
        raise NotImplementedError

    def get(
        self,
        conversation_id: ConversationId,
        *,
        workspace_id: WorkspaceId,
    ) -> Conversation | None:
        raise NotImplementedError

    def list(
        self,
        *,
        workspace_id: WorkspaceId,
    ) -> tuple[Conversation, ...]:
        raise NotImplementedError

    def rename(
        self,
        conversation_id: ConversationId,
        title: str,
        *,
        workspace_id: WorkspaceId,
    ) -> Conversation:
        raise NotImplementedError

    def delete(
        self,
        conversation_id: ConversationId,
        *,
        workspace_id: WorkspaceId,
    ) -> None:
        raise NotImplementedError

    def append_turn(
        self,
        conversation_id: ConversationId,
        turn: ConversationTurn,
        *,
        workspace_id: WorkspaceId,
    ) -> Conversation:
        raise NotImplementedError

    def list_turns(
        self,
        conversation_id: ConversationId,
        *,
        workspace_id: WorkspaceId,
    ) -> tuple[ConversationTurn, ...]:
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
