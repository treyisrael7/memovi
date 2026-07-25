"""Shared capability argument schema validation.

Used by CapabilityInvoker (at invoke time) and ExecutionPlanValidator
(at plan time) so planning and execution share one schema contract.
"""

from __future__ import annotations

from collections.abc import Mapping

from memovi_automation.domain.exceptions import InvalidCapabilityArgumentsError
from memovi_automation.domain.value_objects import CapabilityMetadata, CapabilityParameter

_TYPE_CHECKS: dict[str, type | tuple[type, ...]] = {
    "string": str,
    "integer": int,
    "number": (int, float),
    "boolean": bool,
    "object": Mapping,
    "array": (list, tuple),
}


def validate_capability_arguments(
    arguments: Mapping[str, object],
    metadata: CapabilityMetadata,
) -> dict[str, object]:
    """Validate arguments against capability metadata and return a clean copy."""
    parameters = metadata.parameter_map()
    unknown = sorted(set(arguments) - set(parameters))
    if unknown:
        raise InvalidCapabilityArgumentsError(
            f"Unknown arguments for capability '{metadata.id}': {', '.join(unknown)}.",
        )

    missing = sorted(
        parameter.name
        for parameter in metadata.parameters
        if parameter.required and parameter.name not in arguments
    )
    if missing:
        raise InvalidCapabilityArgumentsError(
            f"Missing required arguments for capability '{metadata.id}': {', '.join(missing)}.",
        )

    validated: dict[str, object] = {}
    for name, value in arguments.items():
        parameter = parameters[name]
        validate_parameter_value(parameter, value)
        validated[name] = value
    return validated


def validate_parameter_value(parameter: CapabilityParameter, value: object) -> None:
    expected = _TYPE_CHECKS[parameter.type]
    if parameter.type == "boolean" and isinstance(value, bool):
        return
    if parameter.type == "integer" and isinstance(value, bool):
        raise InvalidCapabilityArgumentsError(
            f"Argument '{parameter.name}' must be of type integer.",
        )
    if parameter.type == "number" and isinstance(value, bool):
        raise InvalidCapabilityArgumentsError(
            f"Argument '{parameter.name}' must be of type number.",
        )
    if not isinstance(value, expected):
        raise InvalidCapabilityArgumentsError(
            f"Argument '{parameter.name}' must be of type {parameter.type}.",
        )
