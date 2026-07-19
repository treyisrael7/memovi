from dataclasses import dataclass

from memovi_models.domain.exceptions import InvalidModelError
from memovi_models.domain.value_objects.model_capabilities import ModelCapabilities


@dataclass(frozen=True, slots=True)
class ModelMetadata:
    """Immutable discovery metadata for a single model offered by a provider."""

    id: str
    provider_id: str
    display_name: str
    capabilities: ModelCapabilities
    context_window: int | None = None
    description: str = ""

    def __post_init__(self) -> None:
        model_id = self.id.strip()
        provider_id = self.provider_id.strip().lower()
        display_name = self.display_name.strip()
        description = self.description.strip()

        if not model_id:
            raise InvalidModelError("Model metadata id is required.")
        if not provider_id:
            raise InvalidModelError("Model metadata provider_id is required.")
        if not display_name:
            raise InvalidModelError("Model metadata display_name is required.")
        if not isinstance(self.capabilities, ModelCapabilities):
            raise InvalidModelError("Model metadata capabilities must be ModelCapabilities.")
        if self.context_window is not None and self.context_window <= 0:
            raise InvalidModelError("Model metadata context_window must be positive when set.")

        object.__setattr__(self, "id", model_id)
        object.__setattr__(self, "provider_id", provider_id)
        object.__setattr__(self, "display_name", display_name)
        object.__setattr__(self, "description", description)
