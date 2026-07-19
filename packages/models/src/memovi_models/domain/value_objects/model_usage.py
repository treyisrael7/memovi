from dataclasses import dataclass

from memovi_models.domain.exceptions import InvalidModelError


@dataclass(frozen=True, slots=True)
class ModelUsage:
    """Optional token usage reported by a provider."""

    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None

    def __post_init__(self) -> None:
        for name in ("input_tokens", "output_tokens", "total_tokens"):
            value = getattr(self, name)
            if value is not None and value < 0:
                raise InvalidModelError(f"Model usage {name} cannot be negative.")
