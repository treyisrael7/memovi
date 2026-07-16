import pytest
from memovi_search.domain.providers import EmbeddingProvider
from memovi_search.domain.value_objects import EmbeddingVector
from memovi_search.infrastructure.providers import (
    EmbeddingProviderConfig,
    EmbeddingProviderKind,
    OllamaEmbeddingProvider,
    OpenAIEmbeddingProvider,
    SentenceTransformerEmbeddingProvider,
    build_embedding_provider,
)


class FakeEmbeddingProvider:
    def embed(self, text: str) -> EmbeddingVector:
        return EmbeddingVector(values=[0.1, 0.2], dimensions=2)

    def embed_many(self, texts: list[str]) -> list[EmbeddingVector]:
        return [self.embed(text) for text in texts]


def test_fake_provider_conforms_to_embedding_provider_protocol() -> None:
    provider = FakeEmbeddingProvider()

    assert isinstance(provider, EmbeddingProvider)


def test_placeholder_providers_conform_to_protocol() -> None:
    assert isinstance(OpenAIEmbeddingProvider(), EmbeddingProvider)
    assert isinstance(OllamaEmbeddingProvider(), EmbeddingProvider)
    assert isinstance(SentenceTransformerEmbeddingProvider(), EmbeddingProvider)


def test_placeholder_providers_raise_not_implemented() -> None:
    providers: list[EmbeddingProvider] = [
        OpenAIEmbeddingProvider(),
        OllamaEmbeddingProvider(),
        SentenceTransformerEmbeddingProvider(),
    ]

    for provider in providers:
        with pytest.raises(NotImplementedError):
            provider.embed("hello")
        with pytest.raises(NotImplementedError):
            provider.embed_many(["hello"])


def test_build_embedding_provider_selects_configured_kind() -> None:
    openai = build_embedding_provider(
        EmbeddingProviderConfig(kind=EmbeddingProviderKind.OPENAI),
    )
    ollama = build_embedding_provider(
        EmbeddingProviderConfig(kind=EmbeddingProviderKind.OLLAMA),
    )
    sentence = build_embedding_provider(
        EmbeddingProviderConfig(kind=EmbeddingProviderKind.SENTENCE_TRANSFORMER),
    )

    assert isinstance(openai, OpenAIEmbeddingProvider)
    assert isinstance(ollama, OllamaEmbeddingProvider)
    assert isinstance(sentence, SentenceTransformerEmbeddingProvider)
