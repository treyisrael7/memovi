import uuid
from dataclasses import dataclass

from memovi_intelligence.domain.exceptions import InvalidReasoningRequestIdError


@dataclass(frozen=True, slots=True)
class ReasoningRequestId:
    """Stable identifier for a reasoning request."""

    value: str

    @classmethod
    def new(cls) -> ReasoningRequestId:
        return cls(str(uuid.uuid4()))

    def __post_init__(self) -> None:
        try:
            parsed = uuid.UUID(self.value)
        except ValueError as exc:
            raise InvalidReasoningRequestIdError(
                "Reasoning request ID must be a valid UUID.",
            ) from exc

        object.__setattr__(self, "value", str(parsed))

    def __str__(self) -> str:
        return self.value
