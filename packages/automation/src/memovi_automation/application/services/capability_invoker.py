from collections.abc import Mapping
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeoutError
from time import perf_counter

from memovi_automation.application.ports import Capability
from memovi_automation.application.services.capability_registry import CapabilityRegistry
from memovi_automation.domain.exceptions import (
    AutomationDomainError,
    CapabilityCancelledError,
    CapabilityExecutionError,
    CapabilityTimeoutError,
    InvalidCapabilityArgumentsError,
    UnknownCapabilityError,
)
from memovi_automation.domain.value_objects import (
    DEFAULT_EXECUTION_POLICY,
    CapabilityContext,
    CapabilityError,
    CapabilityExecutionPolicy,
    CapabilityMetadata,
    CapabilityParameter,
    CapabilityRequest,
    CapabilityResult,
)

_TYPE_CHECKS: dict[str, type | tuple[type, ...]] = {
    "string": str,
    "integer": int,
    "number": (int, float),
    "boolean": bool,
    "object": Mapping,
    "array": (list, tuple),
}


class CapabilityInvoker:
    """Validates and invokes capabilities resolved through a CapabilityRegistry.

    Returns CapabilityResult for invocation outcomes (success, failure, timeout,
    cancellation, unknown capability). Raises for invalid argument schemas.
    Does not retry or orchestrate multi-step workflows.
    """

    def __init__(
        self,
        *,
        registry: CapabilityRegistry,
        default_policy: CapabilityExecutionPolicy | None = None,
    ) -> None:
        self._registry = registry
        self._default_policy = DEFAULT_EXECUTION_POLICY if default_policy is None else default_policy

    @property
    def registry(self) -> CapabilityRegistry:
        return self._registry

    def invoke(
        self,
        request: CapabilityRequest,
        context: CapabilityContext,
    ) -> CapabilityResult:
        started = perf_counter()
        try:
            capability = self._registry.get(request.capability_id)
        except UnknownCapabilityError as exc:
            return CapabilityResult.failure_result(
                request_id=request.id,
                capability_id=request.capability_id,
                error=CapabilityError(
                    code="unknown_capability",
                    message=str(exc),
                    details={"capability_id": request.capability_id},
                ),
                duration=perf_counter() - started,
            )

        metadata = capability.metadata()
        if metadata.id != request.capability_id:
            raise InvalidCapabilityArgumentsError(
                f"Capability metadata id '{metadata.id}' does not match "
                f"request capability_id '{request.capability_id}'.",
            )

        validated = _validate_arguments(request.arguments, metadata)
        policy = request.policy if request.policy is not None else self._default_policy

        if policy.cancellable and context.is_cancelled():
            return _cancelled_result(request, started)

        validated_request = CapabilityRequest(
            capability_id=request.capability_id,
            arguments=validated,
            id=request.id,
            policy=request.policy,
        )
        try:
            output = _invoke_capability(
                capability,
                validated_request,
                context,
                policy=policy,
            )
        except CapabilityCancelledError:
            return _cancelled_result(request, started)
        except CapabilityTimeoutError as exc:
            return CapabilityResult.failure_result(
                request_id=request.id,
                capability_id=request.capability_id,
                error=CapabilityError(
                    code="timeout",
                    message=str(exc),
                    details={"timeout_seconds": policy.timeout_seconds},
                ),
                duration=perf_counter() - started,
                timed_out=True,
                metadata=_execution_metadata(policy, validated),
            )
        except CapabilityExecutionError as exc:
            return CapabilityResult.failure_result(
                request_id=request.id,
                capability_id=request.capability_id,
                error=CapabilityError(
                    code=exc.code,
                    message=str(exc),
                    details=exc.details,
                ),
                duration=perf_counter() - started,
                metadata=_execution_metadata(policy, validated),
            )
        except AutomationDomainError:
            raise
        except Exception as exc:
            return CapabilityResult.failure_result(
                request_id=request.id,
                capability_id=request.capability_id,
                error=CapabilityError(
                    code="execution_failed",
                    message=f"Capability '{request.capability_id}' failed during execution.",
                    details={"exception_type": type(exc).__name__},
                ),
                duration=perf_counter() - started,
                metadata=_execution_metadata(policy, validated),
            )

        if policy.cancellable and context.is_cancelled():
            return _cancelled_result(request, started)

        return CapabilityResult.success_result(
            request_id=request.id,
            capability_id=request.capability_id,
            output=output,
            duration=perf_counter() - started,
            metadata=_execution_metadata(policy, validated),
        )


def _invoke_capability(
    capability: Capability,
    request: CapabilityRequest,
    context: CapabilityContext,
    *,
    policy: CapabilityExecutionPolicy,
) -> object:
    timeout_seconds = policy.timeout_seconds
    if timeout_seconds is None:
        if policy.cancellable:
            context.check_cancelled()
        return capability.execute(request, context)

    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(capability.execute, request, context)
        try:
            return future.result(timeout=timeout_seconds)
        except FuturesTimeoutError as exc:
            future.cancel()
            if policy.cancellable:
                context.cancellation.cancel()
            raise CapabilityTimeoutError(
                f"Capability '{request.capability_id}' timed out after "
                f"{timeout_seconds} seconds.",
            ) from exc


def _validate_arguments(
    arguments: Mapping[str, object],
    metadata: CapabilityMetadata,
) -> dict[str, object]:
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
        _validate_parameter_value(parameter, value)
        validated[name] = value
    return validated


def _validate_parameter_value(parameter: CapabilityParameter, value: object) -> None:
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


def _execution_metadata(
    policy: CapabilityExecutionPolicy,
    arguments: Mapping[str, object],
) -> dict[str, object]:
    return {
        "argument_count": len(arguments),
        "timeout_seconds": policy.timeout_seconds,
        "cancellable": policy.cancellable,
    }


def _cancelled_result(request: CapabilityRequest, started: float) -> CapabilityResult:
    return CapabilityResult.failure_result(
        request_id=request.id,
        capability_id=request.capability_id,
        error=CapabilityError(
            code="cancelled",
            message=f"Capability '{request.capability_id}' was cancelled.",
        ),
        duration=perf_counter() - started,
        cancelled=True,
    )
