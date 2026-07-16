import pytest
from memovi_search.domain.exceptions import InvalidEmbeddingError
from memovi_search.domain.value_objects import EmbeddingVector


def test_embedding_vector_accepts_matching_dimensions() -> None:
    vector = EmbeddingVector(values=[0.1, 0.2, 0.3], dimensions=3)

    assert vector.values == [0.1, 0.2, 0.3]
    assert vector.dimensions == 3


def test_embedding_vector_rejects_empty_values() -> None:
    with pytest.raises(InvalidEmbeddingError):
        EmbeddingVector(values=[], dimensions=0)


def test_embedding_vector_rejects_dimension_mismatch() -> None:
    with pytest.raises(InvalidEmbeddingError):
        EmbeddingVector(values=[0.1, 0.2], dimensions=3)


def test_embedding_vector_copies_values() -> None:
    source = [0.4, 0.5]
    vector = EmbeddingVector(values=source, dimensions=2)

    source.append(0.6)

    assert vector.values == [0.4, 0.5]
