"""Validate workflow definitions and runtime variable bindings."""

from __future__ import annotations

from collections.abc import Mapping

from memovi_automation.application.services.capability_registry import CapabilityRegistry
from memovi_automation.domain.exceptions import InvalidWorkflowError
from memovi_automation.domain.value_objects.workflow import (
    WorkflowContext,
    WorkflowDefinition,
    extract_variable_references,
)


class WorkflowValidator:
    """Structural and registry-aware validation for workflows.

    Does not execute capabilities. Capability argument schemas are validated
    later when the Capability Planner materializes each step.
    """

    def __init__(self, *, registry: CapabilityRegistry) -> None:
        self._registry = registry

    def validate_definition(self, definition: WorkflowDefinition) -> WorkflowDefinition:
        """Validate a workflow definition against the capability registry."""
        known_steps: set[str] = set()
        declared_vars = {variable.name for variable in definition.variables}

        for capability_id in definition.required_capabilities:
            if not self._registry.contains(capability_id):
                raise InvalidWorkflowError(
                    f"Required capability '{capability_id}' is not registered.",
                    code="unknown_capability",
                    details={"capability_id": capability_id},
                )

        for step in definition.steps:
            if not self._registry.contains(step.capability_id):
                raise InvalidWorkflowError(
                    f"Step '{step.step_id}' references unknown capability "
                    f"'{step.capability_id}'.",
                    code="unknown_capability",
                    details={
                        "step_id": step.step_id,
                        "capability_id": step.capability_id,
                    },
                )
            capability = self._registry.get(step.capability_id)
            supported = getattr(capability, "supported_operations", None)
            if callable(supported):
                operations = supported()
                if step.operation not in operations:
                    raise InvalidWorkflowError(
                        f"Step '{step.step_id}' operation '{step.operation}' "
                        f"is not supported by '{step.capability_id}'.",
                        code="unsupported_operation",
                        details={
                            "step_id": step.step_id,
                            "capability_id": step.capability_id,
                            "operation": step.operation,
                        },
                    )

            for ref in extract_variable_references(dict(step.input_mapping)):
                if ref.startswith("steps."):
                    parts = ref.split(".")
                    if len(parts) < 2 or not parts[1]:
                        raise InvalidWorkflowError(
                            f"Step '{step.step_id}' has an invalid steps reference.",
                            code="invalid_reference",
                            details={"step_id": step.step_id, "reference": ref},
                        )
                    dep_step = parts[1]
                    if dep_step not in known_steps:
                        raise InvalidWorkflowError(
                            f"Step '{step.step_id}' references unavailable step "
                            f"'{dep_step}'.",
                            code="invalid_reference",
                            details={
                                "step_id": step.step_id,
                                "reference": ref,
                                "depends_on": dep_step,
                            },
                        )
                elif ref not in declared_vars:
                    raise InvalidWorkflowError(
                        f"Step '{step.step_id}' references undeclared variable "
                        f"'{ref}'.",
                        code="undeclared_variable",
                        details={"step_id": step.step_id, "variable": ref},
                    )

            known_steps.add(step.step_id)

        for output_name in definition.expected_outputs:
            # Expected outputs are names that should appear in the final context
            # (from variables or output_mapping bindings). Soft check only.
            if not output_name:
                raise InvalidWorkflowError(
                    "Expected output names cannot be blank.",
                    code="invalid_expected_output",
                )

        return definition

    def validate_variables(
        self,
        definition: WorkflowDefinition,
        variables: Mapping[str, object] | None,
    ) -> WorkflowContext:
        """Validate and normalize runtime variables before execution."""
        provided = {} if variables is None else dict(variables)
        unknown = sorted(set(provided) - {v.name for v in definition.variables})
        if unknown:
            raise InvalidWorkflowError(
                f"Unknown workflow variables: {', '.join(unknown)}.",
                code="unknown_variable",
                details={"variables": unknown},
            )

        resolved: dict[str, object] = {}
        for variable in definition.variables:
            if variable.name in provided:
                value = provided[variable.name]
            elif variable.default is not None:
                value = variable.default
            elif variable.required:
                raise InvalidWorkflowError(
                    f"Required workflow variable '{variable.name}' is missing.",
                    code="missing_variable",
                    details={"variable": variable.name},
                )
            else:
                # Optional unbound variables resolve to None so mappings can omit them.
                resolved[variable.name] = None
                continue
            resolved[variable.name] = _coerce_variable(variable.name, variable.type, value)

        return WorkflowContext(variables=resolved)


def _coerce_variable(name: str, var_type: str, value: object) -> object:
    if var_type == "string" or var_type == "path":
        if value is None:
            raise InvalidWorkflowError(
                f"Variable '{name}' cannot be null.",
                code="invalid_variable_value",
                details={"variable": name},
            )
        text = str(value).strip()
        if not text:
            raise InvalidWorkflowError(
                f"Variable '{name}' cannot be blank.",
                code="invalid_variable_value",
                details={"variable": name},
            )
        return text
    if var_type == "number":
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            try:
                if isinstance(value, str) and "." in value:
                    return float(value)
                return int(str(value))
            except (TypeError, ValueError) as exc:
                raise InvalidWorkflowError(
                    f"Variable '{name}' must be a number.",
                    code="invalid_variable_value",
                    details={"variable": name},
                ) from exc
        return value
    if var_type == "boolean":
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered in {"true", "1", "yes"}:
                return True
            if lowered in {"false", "0", "no"}:
                return False
        raise InvalidWorkflowError(
            f"Variable '{name}' must be a boolean.",
            code="invalid_variable_value",
            details={"variable": name},
        )
    raise InvalidWorkflowError(
        f"Unsupported variable type '{var_type}'.",
        code="invalid_variable",
        details={"variable": name, "type": var_type},
    )
