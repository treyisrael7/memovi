from datetime import UTC, datetime, timedelta

import pytest
from memovi_intelligence.domain.exceptions import ConversationNotFoundError
from memovi_intelligence.domain.value_objects import (
    Citation,
    ConversationId,
    ConversationRole,
    ConversationTurn,
)
from memovi_intelligence.infrastructure import SqlAlchemyConversationRepository
from memovi_intelligence.infrastructure.persistence.models import Base
from memovi_shared import WorkspaceId
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

WS = WorkspaceId.default()


def _build_session_factory() -> tuple[sessionmaker[Session], object]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False), engine


def _turn(
    role: ConversationRole,
    content: str,
    *,
    base: datetime,
    seconds: int = 0,
    citations: tuple[Citation, ...] = (),
) -> ConversationTurn:
    return ConversationTurn(
        role=role,
        content=content,
        timestamp=base + timedelta(seconds=seconds),
        citations=citations,
    )


def test_create_and_retrieve_conversation() -> None:
    session_factory, engine = _build_session_factory()

    with session_factory() as session:
        repository = SqlAlchemyConversationRepository(session)
        created = repository.create(workspace_id=WS)
        session.commit()
        conversation_id = created.id

    with session_factory() as session:
        repository = SqlAlchemyConversationRepository(session)
        loaded = repository.get(conversation_id, workspace_id=WS)

        assert loaded is not None
        assert loaded.id == conversation_id
        assert loaded.workspace_id == WS
        assert loaded.turns == ()
        assert loaded.created_at.tzinfo is UTC
        assert loaded.updated_at == loaded.created_at

    engine.dispose()


def test_append_message_and_list_turns() -> None:
    session_factory, engine = _build_session_factory()
    citation = Citation(
        document_id="doc-1",
        chunk_id="chunk-1",
        document_title="Overview",
        score=0.91,
    )

    with session_factory() as session:
        repository = SqlAlchemyConversationRepository(session)
        conversation = repository.create(workspace_id=WS)
        base = conversation.created_at
        repository.append_turn(
            conversation.id,
            _turn(ConversationRole.USER, "What is Memovi?", base=base, seconds=1),
            workspace_id=WS,
        )
        repository.append_turn(
            conversation.id,
            _turn(
                ConversationRole.ASSISTANT,
                "A knowledge platform.",
                base=base,
                seconds=2,
                citations=(citation,),
            ),
            workspace_id=WS,
        )
        session.commit()
        conversation_id = conversation.id

    with session_factory() as session:
        repository = SqlAlchemyConversationRepository(session)
        turns = repository.list_turns(conversation_id, workspace_id=WS)
        loaded = repository.get(conversation_id, workspace_id=WS)

        assert [turn.content for turn in turns] == [
            "What is Memovi?",
            "A knowledge platform.",
        ]
        assert turns[1].citations == (citation,)
        assert loaded is not None
        assert loaded.turns == turns
        assert loaded.updated_at == turns[-1].timestamp

    engine.dispose()


def test_multiple_conversations_are_isolated() -> None:
    session_factory, engine = _build_session_factory()

    with session_factory() as session:
        repository = SqlAlchemyConversationRepository(session)
        first = repository.create(workspace_id=WS)
        second = repository.create(workspace_id=WS)
        repository.append_turn(
            first.id,
            _turn(ConversationRole.USER, "first-only", base=first.created_at, seconds=1),
            workspace_id=WS,
        )
        repository.append_turn(
            second.id,
            _turn(ConversationRole.USER, "second-only", base=second.created_at, seconds=2),
            workspace_id=WS,
        )
        session.commit()
        first_id, second_id = first.id, second.id

    with session_factory() as session:
        repository = SqlAlchemyConversationRepository(session)
        assert [turn.content for turn in repository.list_turns(first_id, workspace_id=WS)] == [
            "first-only"
        ]
        assert [turn.content for turn in repository.list_turns(second_id, workspace_id=WS)] == [
            "second-only"
        ]

    engine.dispose()


def test_workspace_isolation_hides_foreign_conversations() -> None:
    session_factory, engine = _build_session_factory()
    other = WorkspaceId.new()

    with session_factory() as session:
        repository = SqlAlchemyConversationRepository(session)
        conversation = repository.create(workspace_id=WS)
        session.commit()
        conversation_id = conversation.id

    with session_factory() as session:
        repository = SqlAlchemyConversationRepository(session)
        assert repository.get(conversation_id, workspace_id=other) is None

    engine.dispose()


def test_ordering_preserves_append_sequence() -> None:
    session_factory, engine = _build_session_factory()

    with session_factory() as session:
        repository = SqlAlchemyConversationRepository(session)
        conversation = repository.create(workspace_id=WS)
        base = conversation.created_at
        for index, content in enumerate(("one", "two", "three", "four"), start=1):
            role = ConversationRole.USER if index % 2 else ConversationRole.ASSISTANT
            repository.append_turn(
                conversation.id,
                _turn(role, content, base=base, seconds=index),
                workspace_id=WS,
            )
        session.commit()
        conversation_id = conversation.id

    with session_factory() as session:
        repository = SqlAlchemyConversationRepository(session)
        assert [turn.content for turn in repository.list_turns(conversation_id, workspace_id=WS)] == [
            "one",
            "two",
            "three",
            "four",
        ]

    engine.dispose()


def test_empty_conversation_has_no_turns() -> None:
    session_factory, engine = _build_session_factory()

    with session_factory() as session:
        repository = SqlAlchemyConversationRepository(session)
        conversation = repository.create(workspace_id=WS)
        session.commit()
        assert repository.list_turns(conversation.id, workspace_id=WS) == ()

    engine.dispose()


def test_large_histories_round_trip() -> None:
    session_factory, engine = _build_session_factory()
    turn_count = 120

    with session_factory() as session:
        repository = SqlAlchemyConversationRepository(session)
        conversation = repository.create(workspace_id=WS)
        base = conversation.created_at
        for index in range(turn_count):
            role = ConversationRole.USER if index % 2 == 0 else ConversationRole.ASSISTANT
            repository.append_turn(
                conversation.id,
                _turn(role, f"turn-{index}", base=base, seconds=index + 1),
                workspace_id=WS,
            )
        session.commit()
        conversation_id = conversation.id

    with session_factory() as session:
        repository = SqlAlchemyConversationRepository(session)
        turns = repository.list_turns(conversation_id, workspace_id=WS)
        assert len(turns) == turn_count
        assert turns[0].content == "turn-0"
        assert turns[-1].content == f"turn-{turn_count - 1}"

    engine.dispose()


def test_persistence_across_sessions() -> None:
    session_factory, engine = _build_session_factory()

    with session_factory() as session:
        repository = SqlAlchemyConversationRepository(session)
        conversation = repository.create(workspace_id=WS)
        base = conversation.created_at
        repository.append_turn(
            conversation.id,
            _turn(
                ConversationRole.USER,
                "persisted across sessions",
                base=base,
                seconds=1,
            ),
            workspace_id=WS,
        )
        session.commit()
        conversation_id = conversation.id

    with session_factory() as session:
        repository = SqlAlchemyConversationRepository(session)
        loaded = repository.get(conversation_id, workspace_id=WS)
        assert loaded is not None
        assert loaded.turns[0].content == "persisted across sessions"

        repository.append_turn(
            conversation_id,
            _turn(ConversationRole.ASSISTANT, "still here", base=base, seconds=2),
            workspace_id=WS,
        )
        session.commit()

    with session_factory() as session:
        repository = SqlAlchemyConversationRepository(session)
        reloaded = repository.get(conversation_id, workspace_id=WS)
        assert reloaded is not None
        assert [turn.content for turn in reloaded.turns] == [
            "persisted across sessions",
            "still here",
        ]

    engine.dispose()


def test_missing_conversation_get_returns_none() -> None:
    session_factory, engine = _build_session_factory()

    with session_factory() as session:
        repository = SqlAlchemyConversationRepository(session)
        assert repository.get(ConversationId.new(), workspace_id=WS) is None

    engine.dispose()


def test_missing_conversation_append_and_list_raise() -> None:
    session_factory, engine = _build_session_factory()
    missing = ConversationId.new()

    with session_factory() as session:
        repository = SqlAlchemyConversationRepository(session)
        with pytest.raises(ConversationNotFoundError):
            repository.append_turn(
                missing,
                _turn(
                    ConversationRole.USER,
                    "orphan",
                    base=datetime.now(UTC),
                    seconds=1,
                ),
                workspace_id=WS,
            )
        with pytest.raises(ConversationNotFoundError):
            repository.list_turns(missing, workspace_id=WS)

    engine.dispose()


def test_delete_conversation_removes_history() -> None:
    session_factory, engine = _build_session_factory()

    with session_factory() as session:
        repository = SqlAlchemyConversationRepository(session)
        conversation = repository.create(workspace_id=WS)
        repository.append_turn(
            conversation.id,
            _turn(
                ConversationRole.USER,
                "to be deleted",
                base=datetime.now(UTC),
                seconds=1,
            ),
            workspace_id=WS,
        )
        session.commit()
        conversation_id = conversation.id

    with session_factory() as session:
        repository = SqlAlchemyConversationRepository(session)
        repository.delete(conversation_id, workspace_id=WS)
        session.commit()
        assert repository.get(conversation_id, workspace_id=WS) is None

    engine.dispose()
