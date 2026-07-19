from dataclasses import dataclass

from memovi_models.domain.exceptions import InvalidModelError

_ROLES = frozenset({"system", "user", "assistant", "tool"})


@dataclass(frozen=True, slots=True)
class ModelMessage:
    """Provider-neutral chat message."""

    role: str
    content: str

    def __post_init__(self) -> None:
        role = self.role.strip().lower()
        if role not in _ROLES:
            raise InvalidModelError(
                f"Model message role must be one of: {', '.join(sorted(_ROLES))}.",
            )
        if not isinstance(self.content, str):
            raise InvalidModelError("Model message content must be a string.")
        object.__setattr__(self, "role", role)
        object.__setattr__(self, "content", self.content)
