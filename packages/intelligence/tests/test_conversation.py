from dataclasses import FrozenInstanceError
from datetime import UTC, datetime, timedelta

import pytest
from memovi_intelligence.application.services import ConversationService
from memovi_intelligence.domain.entities import Conversation
from memovi_intelligence.domain.exceptions import (
    ConversationNotFoundError,
    InvalidConversationError,
    InvalidConversationIdError,
)
from memovi_intelligence.domain.value_objects import (
    Citation,
    ConversationHistory,
    ConversationId,
    ConversationRole,
    ConversationTurn,
)
from memovi_intelligence.infrastructure import InMemoryConversationRepository
from memovi_shared import WorkspaceId


def _turn(
    role: ConversationRole,
    content: str,
    *,
    seconds: int = 0,
    citations: tuple[Citation, ...] = (),
) -> ConversationTurn:
    return ConversationTurn(
        role=role,
        content=content,
        timestamp=datetime(2026, 7, 17, 12, 0, tzinfo=UTC) + timedelta(seconds=seconds),
        citations=citations,
    )


def test_conversation_create_assigns_id_and_empty_history() -> None:
    workspace_id = WorkspaceId.default()
    conversation = Conversation.create(workspace_id=workspace_id)

    assert isinstance(conversation.id, ConversationId)
    assert conversation.workspace_id == workspace_id
    assert conversation.history.is_empty
    assert conversation.turns == ()
    assert conversation.created_at == conversation.updated_at


def test_conversation_id_rejects_invalid_uuid() -> None:
    with pytest.raises(InvalidConversationIdError):
        ConversationId("not-a-uuid")


def test_conversation_service_create_and_append_turns() -> None:
    workspace_id = WorkspaceId.default()
    service = ConversationService(repository=InMemoryConversationRepository())
    conversation = service.create_conversation(workspace_id=workspace_id)

    updated = service.append_user_turn(
        conversation.id,
        "What is Memovi?",
        workspace_id=workspace_id,
    )
    updated = service.append_assistant_turn(
        updated.id,
        "Memovi is a self-hosted knowledge platform.",
        workspace_id=workspace_id,
        citations=(Citation(document_id="doc-1", chunk_id="chunk-1"),),
    )

    assert len(updated.turns) == 2
    assert updated.turns[0].role is ConversationRole.USER
    assert updated.turns[0].content == "What is Memovi?"
    assert updated.turns[1].role is ConversationRole.ASSISTANT
    assert updated.turns[1].citations[0].chunk_id == "chunk-1"
    assert updated.updated_at >= updated.created_at


def test_conversation_history_preserves_append_order() -> None:
    history = ConversationHistory.empty()
    history = history.append(_turn(ConversationRole.USER, "first", seconds=1))
    history = history.append(_turn(ConversationRole.ASSISTANT, "second", seconds=2))
    history = history.append(_turn(ConversationRole.USER, "third", seconds=3))

    assert [turn.content for turn in history.turns] == ["first", "second", "third"]


def test_conversation_history_token_trimming_keeps_recent_turns() -> None:
    history = ConversationHistory(
        turns=(
            _turn(ConversationRole.USER, "alpha " * 20, seconds=1),
            _turn(ConversationRole.ASSISTANT, "beta " * 20, seconds=2),
            _turn(ConversationRole.USER, "gamma " * 20, seconds=3),
            _turn(ConversationRole.ASSISTANT, "delta " * 20, seconds=4),
        ),
    )
    newest_tokens = ConversationHistory(turns=(history.turns[-1],)).estimated_token_count

    trimmed = history.trim(max_turns=10, max_tokens=newest_tokens)

    assert [turn.content for turn in trimmed.turns] == [history.turns[-1].content]
    assert trimmed.estimated_token_count <= newest_tokens


def test_conversation_history_turn_limit_drops_oldest() -> None:
    history = ConversationHistory(
        turns=(
            _turn(ConversationRole.USER, "one", seconds=1),
            _turn(ConversationRole.ASSISTANT, "two", seconds=2),
            _turn(ConversationRole.USER, "three", seconds=3),
        ),
    )

    trimmed = history.trim(max_turns=2, max_tokens=10_000)

    assert [turn.content for turn in trimmed.turns] == ["two", "three"]


def test_conversation_history_never_bypasses_zero_token_budget() -> None:
    history = ConversationHistory(
        turns=(_turn(ConversationRole.USER, "keep me", seconds=1),),
    )

    assert history.trim(max_turns=5, max_tokens=0).is_empty


def test_conversation_service_load_history() -> None:
    workspace_id = WorkspaceId.default()
    service = ConversationService(repository=InMemoryConversationRepository())
    conversation = service.create_conversation(workspace_id=workspace_id)
    service.append_user_turn(conversation.id, "Hello", workspace_id=workspace_id)
    service.append_assistant_turn(conversation.id, "Hi there", workspace_id=workspace_id)

    history = service.load_history(conversation.id, workspace_id=workspace_id)

    assert [turn.role for turn in history.turns] == [
        ConversationRole.USER,
        ConversationRole.ASSISTANT,
    ]
    assert (
        service.get_conversation(conversation.id, workspace_id=workspace_id).turns == history.turns
    )


def test_conversation_service_raises_when_missing() -> None:
    service = ConversationService(repository=InMemoryConversationRepository())

    with pytest.raises(ConversationNotFoundError):
        service.load_history(ConversationId.new(), workspace_id=WorkspaceId.default())


def test_conversation_repository_isolates_workspaces() -> None:
    repo = InMemoryConversationRepository()
    workspace_a = WorkspaceId.new()
    workspace_b = WorkspaceId.new()
    conversation = repo.create(workspace_id=workspace_a)

    assert repo.get(conversation.id, workspace_id=workspace_b) is None
    assert repo.get(conversation.id, workspace_id=workspace_a) is not None


def test_conversation_turn_rejects_blank_content() -> None:
    with pytest.raises(InvalidConversationError):
        _turn(ConversationRole.USER, "   ")


def test_conversation_is_immutable() -> None:
    conversation = Conversation.create(workspace_id=WorkspaceId.default())

    with pytest.raises(FrozenInstanceError):
        conversation.history = ConversationHistory.empty()  # type: ignore[misc]
