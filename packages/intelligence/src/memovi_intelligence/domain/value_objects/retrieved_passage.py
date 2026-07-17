from dataclasses import dataclass

from memovi_intelligence.domain.exceptions import InvalidRetrievedPassageError

MAX_PASSAGE_TEXT_LENGTH = 50_000


@dataclass(frozen=True, slots=True)
class RetrievedPassage:
    """A knowledge snippet prepared for reasoning context assembly."""

    text: str
    source_id: str | None = None
    score: float | None = None

    def __post_init__(self) -> None:
        normalized = self.text.strip()
        if not normalized:
            raise InvalidRetrievedPassageError("Retrieved passage text is required.")
        if len(normalized) > MAX_PASSAGE_TEXT_LENGTH:
            raise InvalidRetrievedPassageError(
                f"Retrieved passage text must be at most {MAX_PASSAGE_TEXT_LENGTH} characters.",
            )
        if self.source_id is not None and not self.source_id.strip():
            raise InvalidRetrievedPassageError("Retrieved passage source ID cannot be blank.")
        if self.score is not None and self.score < 0:
            raise InvalidRetrievedPassageError("Retrieved passage score cannot be negative.")

        object.__setattr__(self, "text", normalized)
        if self.source_id is not None:
            object.__setattr__(self, "source_id", self.source_id.strip())
