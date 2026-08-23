from __future__ import annotations

import pytest
from memovi_search.application.exceptions import (
    EmbeddingProviderError,
    EmbeddingProviderUnavailableError,
    InvalidEmbeddingConfigError,
)
from memovi_search.config import EmbeddingProviderKind, SearchEmbeddingConfig
from memovi_search.domain.value_objects import EmbeddingVector
from memovi_search.infrastructure.persistence.vector import EMBEDDING_VECTOR_DIMENSIONS
from memovi_search.infrastructure.providers import (
    EmbeddingProviderConfig,
    FakeEmbeddingProvider,
    OllamaEmbeddingProvider,
    OpenAIEmbeddingProvider,
    SentenceTransformerEmbeddingProvider,
    build_embedding_provider,
)


def test_search_embedding_config_defaults_to_explicit_fake(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SEARCH_EMBEDDING_PROVIDER", raising=False)
    monkeypatch.delenv("SEARCH_EMBEDDING_MODEL", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    config = SearchEmbeddingConfig.from_env()
    assert config.kind == EmbeddingProviderKind.FAKE
    assert config.model == "fake-embedding-v1"
    assert config.dimensions == EMBEDDING_VECTOR_DIMENSIONS


def test_search_embedding_config_requires_openai_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SEARCH_EMBEDDING_PROVIDER", "openai")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("SEARCH_EMBEDDING_API_KEY", raising=False)
    with pytest.raises(InvalidEmbeddingConfigError, match="OPENAI_API_KEY"):
        SearchEmbeddingConfig.from_env()


def test_search_embedding_config_rejects_unknown_provider() -> None:
    with pytest.raises(InvalidEmbeddingConfigError, match="Unsupported embedding provider"):
        SearchEmbeddingConfig(provider="not-a-provider")


def test_search_embedding_config_rejects_dimension_mismatch() -> None:
    with pytest.raises(InvalidEmbeddingConfigError, match="pgvector"):
        SearchEmbeddingConfig(provider="fake", dimensions=EMBEDDING_VECTOR_DIMENSIONS + 1)


def test_build_embedding_provider_requires_explicit_fake() -> None:
    provider = build_embedding_provider(
        EmbeddingProviderConfig(kind=EmbeddingProviderKind.FAKE),
    )
    assert isinstance(provider, FakeEmbeddingProvider)
    vector = provider.embed("alpha beta")
    assert vector.dimensions == EMBEDDING_VECTOR_DIMENSIONS


def test_build_openai_provider_without_key_fails() -> None:
    with pytest.raises(EmbeddingProviderUnavailableError, match="API key"):
        build_embedding_provider(
            EmbeddingProviderConfig(kind=EmbeddingProviderKind.OPENAI, api_key=None),
        )


class _FakeOpenAIEmbeddingsResponse:
    def __init__(self, vectors: list[list[float]]) -> None:
        self.data = [
            type("Item", (), {"index": index, "embedding": values})()
            for index, values in enumerate(vectors)
        ]


class _FakeOpenAIClient:
    def __init__(self, vectors: list[list[float]]) -> None:
        self._vectors = vectors
        self.embeddings = self

    def create(self, **kwargs: object) -> _FakeOpenAIEmbeddingsResponse:
        assert kwargs["dimensions"] == EMBEDDING_VECTOR_DIMENSIONS
        return _FakeOpenAIEmbeddingsResponse(self._vectors)


def test_openai_embedding_provider_uses_configured_dimensions() -> None:
    values = [0.1] * EMBEDDING_VECTOR_DIMENSIONS
    provider = OpenAIEmbeddingProvider(
        api_key="test-key",
        model="text-embedding-3-small",
        dimensions=EMBEDDING_VECTOR_DIMENSIONS,
        client=_FakeOpenAIClient([values]),
    )
    vector = provider.embed("hello")
    assert vector == EmbeddingVector(values=values, dimensions=EMBEDDING_VECTOR_DIMENSIONS)


def test_openai_embedding_provider_rejects_wrong_dimensions() -> None:
    provider = OpenAIEmbeddingProvider(
        api_key="test-key",
        dimensions=EMBEDDING_VECTOR_DIMENSIONS,
        client=_FakeOpenAIClient([[0.1, 0.2]]),
    )
    with pytest.raises(EmbeddingProviderError, match="dimensions"):
        provider.embed("hello")


class _FakeHttpxResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, object]:
        return self._payload


class _FakeHttpxClient:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload
        self.posts: list[tuple[str, dict[str, object]]] = []

    def post(self, url: str, json: dict[str, object]) -> _FakeHttpxResponse:
        self.posts.append((url, json))
        return _FakeHttpxResponse(self._payload)


def test_ollama_embedding_provider_posts_to_endpoint() -> None:
    values = [0.25] * EMBEDDING_VECTOR_DIMENSIONS
    client = _FakeHttpxClient({"embedding": values})
    provider = OllamaEmbeddingProvider(
        model="all-minilm",
        endpoint="http://ollama.test",
        dimensions=EMBEDDING_VECTOR_DIMENSIONS,
        http_client=client,
    )
    vector = provider.embed("probe")
    assert vector.dimensions == EMBEDDING_VECTOR_DIMENSIONS
    assert client.posts[0][0] == "http://ollama.test/api/embeddings"
    assert client.posts[0][1]["model"] == "all-minilm"


class _FakeSentenceEncoder:
    def __init__(self, values: list[float]) -> None:
        self._values = values

    def encode(self, texts: list[str], normalize_embeddings: bool = True) -> list[list[float]]:
        assert normalize_embeddings is True
        return [list(self._values) for _ in texts]


def test_sentence_transformer_embedding_provider_uses_encoder() -> None:
    values = [0.5] * EMBEDDING_VECTOR_DIMENSIONS
    provider = SentenceTransformerEmbeddingProvider(
        model="all-MiniLM-L6-v2",
        dimensions=EMBEDDING_VECTOR_DIMENSIONS,
        encoder=_FakeSentenceEncoder(values),
    )
    assert provider.provider == "sentence_transformer"
    assert provider.model == "all-MiniLM-L6-v2"
    assert provider.embed_many([]) == []
    vector = provider.embed("single text")
    assert vector.dimensions == EMBEDDING_VECTOR_DIMENSIONS
    vectors = provider.embed_many(["a", "b"])
    assert len(vectors) == 2
    assert vectors[0].dimensions == EMBEDDING_VECTOR_DIMENSIONS


def test_sentence_transformer_embedding_provider_translates_errors() -> None:
    class _FailingEncoder:
        def encode(self, texts: list[str], normalize_embeddings: bool = True) -> list[list[float]]:
            raise RuntimeError("GPU OOM")

    provider = SentenceTransformerEmbeddingProvider(
        encoder=_FailingEncoder(),
    )
    with pytest.raises(EmbeddingProviderError, match="GPU OOM"):
        provider.embed("fail")

    class _NonNumericEncoder:
        def encode(self, texts: list[str], normalize_embeddings: bool = True) -> list[object]:
            return ["not-a-number"]  # type: ignore[list-item]

    bad_provider = SentenceTransformerEmbeddingProvider(
        encoder=_NonNumericEncoder(),
    )
    with pytest.raises(EmbeddingProviderError, match="non-numeric"):
        bad_provider.embed("bad")


def test_openai_embedding_provider_metadata_and_batching() -> None:
    values = [0.1] * EMBEDDING_VECTOR_DIMENSIONS
    provider = OpenAIEmbeddingProvider(
        api_key="test-key",
        model="text-embedding-3-small",
        dimensions=EMBEDDING_VECTOR_DIMENSIONS,
        client=_FakeOpenAIClient([values, values]),
    )
    assert provider.provider == "openai"
    assert provider.model == "text-embedding-3-small"
    assert provider.embed_many([]) == []
    batch = provider.embed_many(["first", "second"])
    assert len(batch) == 2


def test_ollama_embedding_provider_metadata_and_empty() -> None:
    values = [0.25] * EMBEDDING_VECTOR_DIMENSIONS
    client = _FakeHttpxClient({"embedding": values})
    provider = OllamaEmbeddingProvider(
        model="all-minilm",
        endpoint="http://ollama.test",
        dimensions=EMBEDDING_VECTOR_DIMENSIONS,
        http_client=client,
    )
    assert provider.provider == "ollama"
    assert provider.model == "all-minilm"
    assert provider.embed_many([]) == []
    assert len(provider.embed_many(["a", "b"])) == 2
