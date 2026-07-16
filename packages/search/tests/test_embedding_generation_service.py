import pytest
from memovi_search.application.exceptions import EmbeddingGenerationError
from memovi_search.application.services import EmbeddingGenerationService
from memovi_search.domain.value_objects import EmbeddingVector


class FakeEmbeddingProvider:
    def __init__(self) -> None:
        self.embed_calls: list[str] = []
        self.embed_many_calls: list[list[str]] = []

    def embed(self, text: str) -> EmbeddingVector:
        self.embed_calls.append(text)
        return EmbeddingVector(values=[0.25, 0.75], dimensions=2)

    def embed_many(self, texts: list[str]) -> list[EmbeddingVector]:
        self.embed_many_calls.append(list(texts))
        return [
            EmbeddingVector(values=[float(index), float(index) + 0.5], dimensions=2)
            for index, _text in enumerate(texts)
        ]


class MismatchedCountProvider:
    def embed(self, text: str) -> EmbeddingVector:
        return EmbeddingVector(values=[1.0], dimensions=1)

    def embed_many(self, texts: list[str]) -> list[EmbeddingVector]:
        return [EmbeddingVector(values=[1.0], dimensions=1)]


def test_embedding_generation_service_delegates_to_provider() -> None:
    provider = FakeEmbeddingProvider()
    service = EmbeddingGenerationService(provider=provider)

    vector = service.generate("knowledge fragment")
    vectors = service.generate_many(["one", "two"])

    assert vector == EmbeddingVector(values=[0.25, 0.75], dimensions=2)
    assert vectors == [
        EmbeddingVector(values=[0.0, 0.5], dimensions=2),
        EmbeddingVector(values=[1.0, 1.5], dimensions=2),
    ]
    assert provider.embed_calls == ["knowledge fragment"]
    assert provider.embed_many_calls == [["one", "two"]]


def test_embedding_generation_service_rejects_mismatched_batch_size() -> None:
    service = EmbeddingGenerationService(provider=MismatchedCountProvider())

    with pytest.raises(EmbeddingGenerationError):
        service.generate_many(["one", "two"])
