import pytest
from memovi_memory.domain.exceptions import InvalidChunkGeneratorError
from memovi_memory.domain.services import ChunkGenerator

MAX_CHUNK_SIZE = 10


def test_chunk_generator_returns_empty_list_for_empty_document() -> None:
    generator = ChunkGenerator(max_chunk_size=MAX_CHUNK_SIZE)

    assert generator.generate("") == []


def test_chunk_generator_returns_empty_list_for_whitespace_only_document() -> None:
    generator = ChunkGenerator(max_chunk_size=MAX_CHUNK_SIZE)

    assert generator.generate("   \n\t  ") == []


def test_chunk_generator_returns_single_chunk_for_small_document() -> None:
    generator = ChunkGenerator(max_chunk_size=MAX_CHUNK_SIZE)

    drafts = generator.generate("  Short.  ")

    assert len(drafts) == 1
    assert drafts[0].chunk_index.value == 0
    assert drafts[0].text == "Short."


def test_chunk_generator_splits_large_document_into_multiple_chunks() -> None:
    generator = ChunkGenerator(max_chunk_size=MAX_CHUNK_SIZE)
    text = "abcdefghijklmnop"

    drafts = generator.generate(text)

    assert len(drafts) == 2
    assert drafts[0].text == "abcdefghij"
    assert drafts[1].text == "klmnop"


def test_chunk_generator_assigns_sequential_indexes_starting_at_zero() -> None:
    generator = ChunkGenerator(max_chunk_size=4)
    text = "12345678901234567890"

    drafts = generator.generate(text)

    assert [draft.chunk_index.value for draft in drafts] == [0, 1, 2, 3, 4]


def test_chunk_generator_is_deterministic_for_same_input() -> None:
    generator = ChunkGenerator(max_chunk_size=MAX_CHUNK_SIZE)
    text = "Deterministic chunk generation should be stable."

    first = generator.generate(text)
    second = generator.generate(text)

    assert first == second


def test_chunk_generator_omits_empty_chunks() -> None:
    generator = ChunkGenerator(max_chunk_size=3)
    text = "abc   def"

    drafts = generator.generate(text)

    assert len(drafts) == 2
    assert drafts[0].text == "abc"
    assert drafts[1].text == "def"
    assert [draft.chunk_index.value for draft in drafts] == [0, 1]


def test_chunk_generator_rejects_non_positive_max_chunk_size() -> None:
    with pytest.raises(InvalidChunkGeneratorError):
        ChunkGenerator(max_chunk_size=0)

    with pytest.raises(InvalidChunkGeneratorError):
        ChunkGenerator(max_chunk_size=-5)
