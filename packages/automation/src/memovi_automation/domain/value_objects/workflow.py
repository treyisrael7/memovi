"""Immutable workflow contracts for the Workflow Automation Framework.

Workflows are declarative sequences of capability steps. They never invoke
capabilities directly — materialization goes through the Capability Planner
and execution through the Capability Execution Engine.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from types import MappingProxyType
from uuid import uuid4

from memovi_automation.domain.exceptions import InvalidWorkflowError

_VARIABLE_REF = re.compile(r"\$\{([a-zA-Z_][a-zA-Z0-9_\.]*)\}")
_ALLOWED_VARIABLE_TYPES = frozenset({"string", "path", "number", "boolean"})


@dataclass(frozen=True, slots=True)
class WorkflowVariable:
    """Declared input variable for a reusable workflow."""

    name: str
    type: str = "string"
    description: str = ""
    required: bool = True
    default: object | None = None

    def __post_init__(self) -> None:
        name = self.name.strip()
        var_type = self.type.strip().lower() or "string"
        if not name:
            raise InvalidWorkflowError(
                "Workflow variable name is required.",
                code="invalid_variable",
            )
        if not re.fullmatch(r"[a-zA-Z_][a-zA-Z0-9_]*", name):
            raise InvalidWorkflowError(
                f"Invalid workflow variable name '{self.name}'.",
                code="invalid_variable",
                details={"name": self.name},
            )
        if var_type not in _ALLOWED_VARIABLE_TYPES:
            raise InvalidWorkflowError(
                f"Unsupported workflow variable type '{self.type}'.",
                code="invalid_variable",
                details={"name": name, "type": self.type},
            )
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "type", var_type)
        object.__setattr__(self, "description", self.description.strip())


@dataclass(frozen=True, slots=True)
class WorkflowStep:
    """One declarative capability step in a workflow.

    ``input_mapping`` supplies capability arguments. Values may be literals or
    ``${variable}`` / ``${steps.<step_id>.<path>}`` substitutions.
    ``output_mapping`` copies fields from the step result into workflow context
    under the given names (values are dotted paths into the capability output).
    """

    step_id: str
    capability_id: str
    operation: str
    input_mapping: Mapping[str, object] = field(default_factory=dict)
    output_mapping: Mapping[str, str] = field(default_factory=dict)
    expected_result: str | None = None
    description: str = ""

    def __post_init__(self) -> None:
        step_id = self.step_id.strip()
        capability_id = self.capability_id.strip()
        operation = self.operation.strip()
        if not step_id:
            raise InvalidWorkflowError(
                "Workflow step id is required.",
                code="invalid_step",
            )
        if not capability_id:
            raise InvalidWorkflowError(
                "Workflow step capability_id is required.",
                code="invalid_step",
                details={"step_id": step_id},
            )
        if not operation:
            raise InvalidWorkflowError(
                "Workflow step operation is required.",
                code="invalid_step",
                details={"step_id": step_id},
            )
        if not isinstance(self.input_mapping, Mapping):
            raise InvalidWorkflowError(
                "Workflow step input_mapping must be a mapping.",
                code="invalid_step",
                details={"step_id": step_id},
            )
        if not isinstance(self.output_mapping, Mapping):
            raise InvalidWorkflowError(
                "Workflow step output_mapping must be a mapping.",
                code="invalid_step",
                details={"step_id": step_id},
            )
        for key, path in self.output_mapping.items():
            if not str(key).strip() or not isinstance(path, str) or not path.strip():
                raise InvalidWorkflowError(
                    f"Workflow step '{step_id}' has an invalid output_mapping.",
                    code="invalid_step",
                    details={"step_id": step_id},
                )

        expected = None if self.expected_result is None else self.expected_result.strip()
        if self.expected_result is not None and not expected:
            raise InvalidWorkflowError(
                "Workflow step expected_result cannot be blank when provided.",
                code="invalid_step",
                details={"step_id": step_id},
            )

        object.__setattr__(self, "step_id", step_id)
        object.__setattr__(self, "capability_id", capability_id)
        object.__setattr__(self, "operation", operation)
        object.__setattr__(self, "input_mapping", MappingProxyType(dict(self.input_mapping)))
        object.__setattr__(
            self,
            "output_mapping",
            MappingProxyType({str(k): str(v).strip() for k, v in self.output_mapping.items()}),
        )
        object.__setattr__(self, "expected_result", expected)
        object.__setattr__(self, "description", self.description.strip())


@dataclass(frozen=True, slots=True)
class WorkflowDefinition:
    """Human-readable reusable workflow definition."""

    workflow_id: str
    name: str
    description: str
    steps: tuple[WorkflowStep, ...]
    variables: tuple[WorkflowVariable, ...] = ()
    expected_outputs: tuple[str, ...] = ()
    required_capabilities: tuple[str, ...] = ()
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        workflow_id = self.workflow_id.strip()
        name = self.name.strip()
        description = self.description.strip()
        if not workflow_id:
            raise InvalidWorkflowError("Workflow id is required.")
        if not name:
            raise InvalidWorkflowError("Workflow name is required.")
        if not self.steps:
            raise InvalidWorkflowError(
                "Workflow must contain at least one step.",
                code="empty_workflow",
            )

        step_ids = [step.step_id for step in self.steps]
        if len(step_ids) != len(set(step_ids)):
            raise InvalidWorkflowError(
                "Workflow step ids must be unique.",
                code="duplicate_step_id",
            )

        var_names = [variable.name for variable in self.variables]
        if len(var_names) != len(set(var_names)):
            raise InvalidWorkflowError(
                "Workflow variable names must be unique.",
                code="duplicate_variable",
            )

        required = self.required_capabilities or tuple(
            dict.fromkeys(step.capability_id for step in self.steps)
        )
        outputs = tuple(item.strip() for item in self.expected_outputs if str(item).strip())

        object.__setattr__(self, "workflow_id", workflow_id)
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "description", description)
        object.__setattr__(self, "steps", tuple(self.steps))
        object.__setattr__(self, "variables", tuple(self.variables))
        object.__setattr__(self, "expected_outputs", outputs)
        object.__setattr__(self, "required_capabilities", tuple(required))
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))

    def variable_map(self) -> dict[str, WorkflowVariable]:
        return {variable.name: variable for variable in self.variables}

    def step_map(self) -> dict[str, WorkflowStep]:
        return {step.step_id: step for step in self.steps}


@dataclass(frozen=True, slots=True)
class WorkflowContext:
    """Runtime variable + step-output store for a workflow instance."""

    variables: Mapping[str, object] = field(default_factory=dict)
    step_outputs: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "variables", MappingProxyType(dict(self.variables)))
        object.__setattr__(self, "step_outputs", MappingProxyType(dict(self.step_outputs)))

    def with_variables(self, values: Mapping[str, object]) -> WorkflowContext:
        merged = dict(self.variables)
        merged.update(values)
        return WorkflowContext(variables=merged, step_outputs=dict(self.step_outputs))

    def with_step_output(self, step_id: str, output: object) -> WorkflowContext:
        outputs = dict(self.step_outputs)
        outputs[step_id] = output
        return WorkflowContext(variables=dict(self.variables), step_outputs=outputs)

    def with_bound_values(self, values: Mapping[str, object]) -> WorkflowContext:
        """Merge mapped output bindings into the variable namespace."""
        merged = dict(self.variables)
        merged.update(values)
        return WorkflowContext(variables=merged, step_outputs=dict(self.step_outputs))


@dataclass(frozen=True, slots=True)
class WorkflowInstance:
    """A single run of a workflow definition."""

    instance_id: str
    workflow_id: str
    workflow_name: str
    workspace_id: str
    status: str
    context: WorkflowContext
    conversation_id: str | None = None
    correlation_id: str | None = None
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    finished_at: datetime | None = None
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))

    @classmethod
    def create(
        cls,
        *,
        workflow: WorkflowDefinition,
        workspace_id: str,
        context: WorkflowContext,
        conversation_id: str | None = None,
        correlation_id: str | None = None,
        metadata: Mapping[str, object] | None = None,
    ) -> WorkflowInstance:
        instance_id = str(uuid4())
        return cls(
            instance_id=instance_id,
            workflow_id=workflow.workflow_id,
            workflow_name=workflow.name,
            workspace_id=workspace_id.strip(),
            status="running",
            context=context,
            conversation_id=conversation_id,
            correlation_id=correlation_id or instance_id,
            metadata={} if metadata is None else dict(metadata),
        )


@dataclass(frozen=True, slots=True)
class WorkflowStepResult:
    """Outcome of one workflow step after engine submission."""

    step_id: str
    capability_id: str
    operation: str
    execution_id: str | None
    status: str
    output: object | None = None
    error_code: str | None = None
    error_message: str | None = None
    duration: float = 0.0
    plan_id: str | None = None


@dataclass(frozen=True, slots=True)
class WorkflowExecutionResult:
    """Structured result of a workflow run."""

    instance_id: str
    workflow_id: str
    workflow_name: str
    workspace_id: str
    status: str
    completed_steps: tuple[str, ...] = ()
    failed_steps: tuple[str, ...] = ()
    step_results: tuple[WorkflowStepResult, ...] = ()
    duration: float = 0.0
    outputs: Mapping[str, object] = field(default_factory=dict)
    errors: tuple[str, ...] = ()
    audit_references: tuple[str, ...] = ()
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    finished_at: datetime | None = None
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "outputs", MappingProxyType(dict(self.outputs)))
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))
        object.__setattr__(self, "step_results", tuple(self.step_results))
        object.__setattr__(self, "completed_steps", tuple(self.completed_steps))
        object.__setattr__(self, "failed_steps", tuple(self.failed_steps))
        object.__setattr__(self, "errors", tuple(self.errors))
        object.__setattr__(self, "audit_references", tuple(self.audit_references))


@dataclass(frozen=True, slots=True)
class WorkflowHistoryEntry:
    """Persisted summary of a prior workflow execution."""

    instance_id: str
    workflow_id: str
    workflow_name: str
    workspace_id: str
    status: str
    executed_at: datetime
    duration: float
    result_summary: Mapping[str, object]
    executed_capabilities: tuple[str, ...]
    audit_references: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "result_summary",
            MappingProxyType(dict(self.result_summary)),
        )
        object.__setattr__(
            self,
            "executed_capabilities",
            tuple(self.executed_capabilities),
        )
        object.__setattr__(self, "audit_references", tuple(self.audit_references))


def extract_variable_references(value: object) -> tuple[str, ...]:
    """Collect ``${...}`` references from a nested mapping/list/string value."""
    found: list[str] = []
    _collect_refs(value, found)
    return tuple(dict.fromkeys(found))


def _collect_refs(value: object, found: list[str]) -> None:
    if isinstance(value, str):
        found.extend(_VARIABLE_REF.findall(value))
        return
    if isinstance(value, Mapping):
        for item in value.values():
            _collect_refs(item, found)
        return
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for item in value:
            _collect_refs(item, found)


def substitute_value(value: object, context: WorkflowContext) -> object:
    """Resolve ``${var}`` and ``${steps.step_id.path}`` references in a value."""
    if isinstance(value, str):
        return _substitute_string(value, context)
    if isinstance(value, Mapping):
        return {str(key): substitute_value(item, context) for key, item in value.items()}
    if isinstance(value, list):
        return [substitute_value(item, context) for item in value]
    if isinstance(value, tuple):
        return tuple(substitute_value(item, context) for item in value)
    return value


def _substitute_string(template: str, context: WorkflowContext) -> object:
    matches = list(_VARIABLE_REF.finditer(template))
    if not matches:
        return template
    # Entire string is a single reference → preserve non-string types.
    if len(matches) == 1 and matches[0].span() == (0, len(template)):
        return _resolve_reference(matches[0].group(1), context)

    def repl(match: re.Match[str]) -> str:
        resolved = _resolve_reference(match.group(1), context)
        return "" if resolved is None else str(resolved)

    return _VARIABLE_REF.sub(repl, template)


def _resolve_reference(ref: str, context: WorkflowContext) -> object:
    if ref.startswith("steps."):
        remainder = ref[len("steps.") :]
        if not remainder:
            raise InvalidWorkflowError(
                "Empty steps reference.",
                code="unresolved_reference",
                details={"reference": ref},
            )
        parts = remainder.split(".")
        step_id = parts[0]
        if step_id not in context.step_outputs:
            raise InvalidWorkflowError(
                f"Step output '{step_id}' is not available.",
                code="unresolved_reference",
                details={"reference": ref, "step_id": step_id},
            )
        current: object = context.step_outputs[step_id]
        for part in parts[1:]:
            current = _dig(current, part, ref)
        return current

    if ref not in context.variables:
        raise InvalidWorkflowError(
            f"Unknown workflow variable '{ref}'.",
            code="unresolved_reference",
            details={"reference": ref},
        )
    return context.variables[ref]


def _dig(current: object, part: str, ref: str) -> object:
    if isinstance(current, Mapping):
        if part not in current:
            raise InvalidWorkflowError(
                f"Path '{ref}' not found in step output.",
                code="unresolved_reference",
                details={"reference": ref, "missing": part},
            )
        return current[part]
    raise InvalidWorkflowError(
        f"Cannot resolve path '{ref}' against non-mapping output.",
        code="unresolved_reference",
        details={"reference": ref},
    )


def read_output_path(output: object, path: str) -> object:
    """Read a dotted path from a capability output (``$`` / empty = whole output)."""
    cleaned = path.strip()
    if cleaned in {"", "$", "."}:
        return output
    if cleaned.startswith("$."):
        cleaned = cleaned[2:]
    elif cleaned.startswith("$"):
        cleaned = cleaned[1:]
    current: object = output
    for part in cleaned.split("."):
        if not part:
            continue
        current = _dig(current, part, path)
    return current
