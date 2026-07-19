from memovi_automation.application.ports import Capability
from memovi_automation.domain.exceptions import InvalidCapabilityError, UnknownCapabilityError
from memovi_automation.domain.value_objects import CapabilityMetadata, CapabilityPermission


class CapabilityRegistry:
    """Registers and discovers capabilities without executing them.

    Capabilities are registered explicitly through dependency injection.
    There is no global registry and no reflection-based discovery.
    """

    def __init__(self) -> None:
        self._capabilities: dict[str, Capability] = {}

    def register(self, capability: Capability) -> None:
        metadata = capability.metadata()
        capability_id = metadata.id.strip()
        if not capability_id:
            raise InvalidCapabilityError("Cannot register a capability with a blank id.")
        if capability_id in self._capabilities:
            raise InvalidCapabilityError(f"Capability '{capability_id}' is already registered.")
        self._capabilities[capability_id] = capability

    def get(self, capability_id: str) -> Capability:
        capability = self._capabilities.get(capability_id.strip())
        if capability is None:
            raise UnknownCapabilityError(f"Unknown capability '{capability_id}'.")
        return capability

    def list(self) -> tuple[CapabilityMetadata, ...]:
        return tuple(capability.metadata() for capability in self._capabilities.values())

    def metadata(self, capability_id: str) -> CapabilityMetadata:
        return self.get(capability_id).metadata()

    def permissions(self, capability_id: str) -> tuple[CapabilityPermission, ...]:
        return self.metadata(capability_id).permissions

    def contains(self, capability_id: str) -> bool:
        return capability_id.strip() in self._capabilities

    @property
    def ids(self) -> tuple[str, ...]:
        return tuple(self._capabilities.keys())
