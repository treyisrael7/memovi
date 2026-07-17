from __future__ import annotations

import pytest
from memovi_intelligence.application.commands import Reason
from memovi_intelligence.application.services import ContextAssembler, PromptBuilder
from memovi_intelligence.config import IntelligenceConfig
from memovi_intelligence.domain.entities import ReasoningRequest, ReasoningResult
from memovi_intelligence.domain.value_objects import RetrievedKnowledge
from memovi_intelligence.infrastructure import (
    FakeReasoningProvider,
    OpenAIReasoningProvider,
    build_model_gateway,
    serialize_prompt_messages,
)


class StubKnowledgeRetriever:
    def __init__(self, items: tuple[RetrievedKnowledge, ...] = ()) -> None:
        self._items = items

    def retrieve(
        self,
        request: ReasoningRequest,
        *,
        limit: int,
    ) -> tuple[RetrievedKnowledge, ...]:
        return self._items[:limit]


def _memovi_knowledge() -> tuple[RetrievedKnowledge, ...]:
    return (
        RetrievedKnowledge(
            chunk_id="chunk-memovi",
            document_id="doc-memovi",
            text="Memovi is a self-hosted knowledge platform.",
            score=0.95,
            document_title="Memovi",
        ),
        RetrievedKnowledge(
            chunk_id="chunk-knowledge",
            document_id="doc-principles",
            text="Knowledge is the product.",
            score=0.90,
            document_title="Principles",
        ),
        RetrievedKnowledge(
            chunk_id="chunk-ai",
            document_id="doc-principles",
            text="AI is a consumer.",
            score=0.85,
            document_title="Principles",
        ),
    )


def test_intelligence_config_from_env_reads_provider_and_openai_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("INTELLIGENCE_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-5")
    monkeypatch.delenv("INTELLIGENCE_MODEL", raising=False)

    config = IntelligenceConfig.from_env()

    assert config.provider == "openai"
    assert config.model == "gpt-5"


def test_build_model_gateway_registers_both_providers_when_key_present(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("INTELLIGENCE_PROVIDER", "fake")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-5")

    gateway = build_model_gateway()

    assert isinstance(gateway._providers["fake"], FakeReasoningProvider)
    assert isinstance(gateway._providers["openai"], OpenAIReasoningProvider)
    assert gateway.provider_name == "fake"
    assert gateway.model == "fake-reasoning-v1"


def test_provider_switch_is_configuration_only(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-5")
    knowledge = _memovi_knowledge()
    retriever = StubKnowledgeRetriever(knowledge)
    assembler = ContextAssembler(knowledge_retriever=retriever)
    builder = PromptBuilder()
    request = ReasoningRequest.create(query="What is Memovi?")

    monkeypatch.setenv("INTELLIGENCE_PROVIDER", "fake")
    fake_gateway = build_model_gateway()
    fake_result = Reason(
        knowledge_retriever=retriever,
        context_assembler=assembler,
        model_gateway=fake_gateway,
        prompt_builder=builder,
    ).execute(request)

    assert fake_result.provider == "fake"
    assert fake_result.metadata["model"] == "fake-reasoning-v1"
    assert "What is Memovi?" in fake_result.answer

    prompt = builder.build(assembler.assemble(request))
    messages = serialize_prompt_messages(prompt)
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"
    assert isinstance(fake_result, ReasoningResult)
