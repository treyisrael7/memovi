from datetime import timedelta

from memovi_intelligence.application.services import ConversationService
from memovi_intelligence.domain.value_objects import Citation, ConversationRole
from memovi_intelligence.infrastructure import SqlAlchemyConversationRepository
from memovi_intelligence.infrastructure.persistence.models import Base
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool


def _build_session_factory() -> tuple[sessionmaker[Session], object]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False), engine


def test_conversation_service_survives_session_restart() -> None:
    session_factory, engine = _build_session_factory()

    with session_factory() as session:
        service = ConversationService(repository=SqlAlchemyConversationRepository(session))
        conversation = service.create_conversation()
        service.append_user_turn(conversation.id, "Hello durable world")
        service.append_assistant_turn(
            conversation.id,
            "Hello back",
            citations=(Citation(document_id="doc-a", chunk_id="chunk-a", score=0.8),),
        )
        session.commit()
        conversation_id = conversation.id

    with session_factory() as session:
        service = ConversationService(repository=SqlAlchemyConversationRepository(session))
        history = service.load_history(conversation_id)
        assert [turn.role for turn in history.turns] == [
            ConversationRole.USER,
            ConversationRole.ASSISTANT,
        ]
        assert history.turns[0].content == "Hello durable world"
        assert history.turns[1].citations[0].chunk_id == "chunk-a"

        service.append_user_turn(
            conversation_id,
            "Continue chatting",
            timestamp=history.turns[-1].timestamp + timedelta(seconds=1),
        )
        session.commit()

    with session_factory() as session:
        service = ConversationService(repository=SqlAlchemyConversationRepository(session))
        reloaded = service.get_conversation(conversation_id)
        assert [turn.content for turn in reloaded.turns] == [
            "Hello durable world",
            "Hello back",
            "Continue chatting",
        ]

    engine.dispose()
