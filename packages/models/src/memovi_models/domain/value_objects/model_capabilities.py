from dataclasses import dataclass

from memovi_models.domain.exceptions import InvalidModelError


@dataclass(frozen=True, slots=True)
class ModelCapabilities:
    """Provider- or model-advertised capabilities.

    Intelligence should query these flags instead of hardcoding vendor behavior.
    """

    chat: bool = False
    embeddings: bool = False
    streaming: bool = False
    tool_calling: bool = False
    vision: bool = False
    structured_output: bool = False

    def supports(self, capability: str) -> bool:
        name = capability.strip().lower()
        mapping = {
            "chat": self.chat,
            "embeddings": self.embeddings,
            "streaming": self.streaming,
            "tool_calling": self.tool_calling,
            "vision": self.vision,
            "structured_output": self.structured_output,
        }
        if name not in mapping:
            raise InvalidModelError(f"Unknown model capability '{capability}'.")
        return mapping[name]

    def enabled_names(self) -> tuple[str, ...]:
        names: list[str] = []
        if self.chat:
            names.append("chat")
        if self.embeddings:
            names.append("embeddings")
        if self.streaming:
            names.append("streaming")
        if self.tool_calling:
            names.append("tool_calling")
        if self.vision:
            names.append("vision")
        if self.structured_output:
            names.append("structured_output")
        return tuple(names)

    def merge(self, other: ModelCapabilities) -> ModelCapabilities:
        """Return the union of two capability sets (any-true wins)."""
        return ModelCapabilities(
            chat=self.chat or other.chat,
            embeddings=self.embeddings or other.embeddings,
            streaming=self.streaming or other.streaming,
            tool_calling=self.tool_calling or other.tool_calling,
            vision=self.vision or other.vision,
            structured_output=self.structured_output or other.structured_output,
        )
