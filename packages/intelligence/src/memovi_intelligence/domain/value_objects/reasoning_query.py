from dataclasses import dataclass

from memovi_intelligence.domain.exceptions import InvalidReasoningQueryError

MAX_REASONING_QUERY_LENGTH = 8_000


@dataclass(frozen=True, slots=True)
class ReasoningQuery:
    """Natural-language question or instruction supplied to a reasoning workflow."""

    value: str

    def __post_init__(self) -> None:
        normalized = self.value.strip()
        if not normalized:
            raise InvalidReasoningQueryError("Reasoning query is required.")
        if len(normalized) > MAX_REASONING_QUERY_LENGTH:
            raise InvalidReasoningQueryError(
                f"Reasoning query must be at most {MAX_REASONING_QUERY_LENGTH} characters.",
            )

        object.__setattr__(self, "value", normalized)

    def __str__(self) -> str:
        return self.value
