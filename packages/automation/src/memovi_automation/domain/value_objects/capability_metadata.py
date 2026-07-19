from dataclasses import dataclass

from memovi_automation.domain.exceptions import InvalidCapabilityError
from memovi_automation.domain.value_objects.capability_parameter import CapabilityParameter
from memovi_automation.domain.value_objects.capability_permission import CapabilityPermission


@dataclass(frozen=True, slots=True)
class CapabilityMetadata:
    """Immutable discovery metadata for a registered capability."""

    id: str
    description: str
    permissions: tuple[CapabilityPermission, ...] = ()
    parameters: tuple[CapabilityParameter, ...] = ()

    def __post_init__(self) -> None:
        capability_id = self.id.strip()
        description = self.description.strip()

        if not capability_id:
            raise InvalidCapabilityError("Capability metadata id is required.")
        if not description:
            raise InvalidCapabilityError("Capability metadata description is required.")
        if any(not isinstance(permission, CapabilityPermission) for permission in self.permissions):
            raise InvalidCapabilityError("permissions must contain CapabilityPermission instances.")
        if any(not isinstance(parameter, CapabilityParameter) for parameter in self.parameters):
            raise InvalidCapabilityError("parameters must contain CapabilityParameter instances.")

        permission_names = [permission.name for permission in self.permissions]
        if len(permission_names) != len(set(permission_names)):
            raise InvalidCapabilityError("Capability permission names must be unique.")

        parameter_names = [parameter.name for parameter in self.parameters]
        if len(parameter_names) != len(set(parameter_names)):
            raise InvalidCapabilityError("Capability parameter names must be unique.")

        object.__setattr__(self, "id", capability_id)
        object.__setattr__(self, "description", description)
        object.__setattr__(self, "permissions", tuple(self.permissions))
        object.__setattr__(self, "parameters", tuple(self.parameters))

    def parameter_map(self) -> dict[str, CapabilityParameter]:
        return {parameter.name: parameter for parameter in self.parameters}

    def permission_names(self) -> tuple[str, ...]:
        return tuple(permission.name for permission in self.permissions)
