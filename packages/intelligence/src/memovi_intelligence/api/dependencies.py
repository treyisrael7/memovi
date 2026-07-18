from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session as OrmSession

from memovi_intelligence.application.commands import Reason, SendConversationMessage
from memovi_intelligence.application.ports import ConversationRepository, KnowledgeRetriever
from memovi_intelligence.application.services import (
    ContextAssembler,
    ConversationService,
    ModelGateway,
    PromptBuilder,
)
from memovi_intelligence.config import IntelligenceConfig
from memovi_intelligence.infrastructure import (
    FakeKnowledgeRetriever,
    InMemoryConversationRepository,
    build_model_gateway,
)


def get_database_session() -> OrmSession:
    raise RuntimeError("Intelligence database session dependency was not configured.")


DatabaseSession = Annotated[OrmSession, Depends(get_database_session)]


def get_intelligence_config(request: Request) -> IntelligenceConfig:
    config = getattr(request.app.state, "intelligence_config", None)
    if config is None:
        config = IntelligenceConfig.from_env()
        request.app.state.intelligence_config = config
    return config


def get_conversation_repository(request: Request) -> ConversationRepository:
    """Package default: process-local store for isolated tests.

    The composition root overrides this with SqlAlchemyConversationRepository.
    """
    repository = getattr(request.app.state, "conversation_repository", None)
    if repository is None:
        repository = InMemoryConversationRepository()
        request.app.state.conversation_repository = repository
    return repository


def get_knowledge_retriever(request: Request) -> KnowledgeRetriever:
    retriever = getattr(request.app.state, "knowledge_retriever", None)
    if retriever is None:
        retriever = FakeKnowledgeRetriever()
        request.app.state.knowledge_retriever = retriever
    return retriever


def get_model_gateway(request: Request) -> ModelGateway:
    gateway = getattr(request.app.state, "model_gateway", None)
    if gateway is None:
        gateway = build_model_gateway(get_intelligence_config(request))
        request.app.state.model_gateway = gateway
    return gateway


def get_conversation_service(
    repository: Annotated[ConversationRepository, Depends(get_conversation_repository)],
) -> ConversationService:
    return ConversationService(repository=repository)


def get_reason(
    knowledge_retriever: Annotated[KnowledgeRetriever, Depends(get_knowledge_retriever)],
    model_gateway: Annotated[ModelGateway, Depends(get_model_gateway)],
    config: Annotated[IntelligenceConfig, Depends(get_intelligence_config)],
) -> Reason:
    return Reason(
        knowledge_retriever=knowledge_retriever,
        context_assembler=ContextAssembler(
            knowledge_retriever=knowledge_retriever,
            config=config,
        ),
        model_gateway=model_gateway,
        prompt_builder=PromptBuilder(),
    )


def get_send_conversation_message(
    conversations: Annotated[ConversationService, Depends(get_conversation_service)],
    reason: Annotated[Reason, Depends(get_reason)],
) -> SendConversationMessage:
    return SendConversationMessage(
        conversations=conversations,
        reason=reason,
    )
