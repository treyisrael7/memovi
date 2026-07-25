from collections.abc import Mapping
from typing import Final

from memovi_automation.application.services.capability_registry import CapabilityRegistry
from memovi_automation.domain.exceptions import CapabilityExecutionError
from memovi_automation.domain.value_objects import (
    GIT_NETWORK,
    GIT_READ,
    GIT_WRITE,
    CapabilityContext,
    CapabilityMetadata,
    CapabilityParameter,
    CapabilityPermission,
    CapabilityRequest,
)
from memovi_automation.git import operations
from memovi_automation.git.config import GitCapabilityConfig
from memovi_automation.git.errors import (
    EMPTY_MESSAGE,
    INVALID_REF,
    INVALID_REPOSITORY,
    INVALID_TIMEOUT,
    PERMISSION_DENIED,
    UNSUPPORTED_OPERATION,
)
from memovi_automation.git.repo_safety import resolve_repository_path

CAPABILITY_ID: Final = "git"

READ_OPERATIONS: Final[frozenset[str]] = frozenset(
    {
        "detect_repository",
        "repository_info",
        "status",
        "list_branches",
        "commit_history",
        "diff",
    }
)

WRITE_OPERATIONS: Final[frozenset[str]] = frozenset(
    {
        "checkout_branch",
        "create_branch",
        "stage_files",
        "unstage_files",
        "commit",
    }
)

NETWORK_OPERATIONS: Final[frozenset[str]] = frozenset(
    {
        "fetch",
        "pull",
        "push",
    }
)

_ALL_OPERATIONS: Final[frozenset[str]] = READ_OPERATIONS | WRITE_OPERATIONS | NETWORK_OPERATIONS

_GIT_PERMISSIONS: Final[tuple[CapabilityPermission, ...]] = (
    GIT_READ,
    GIT_WRITE,
    GIT_NETWORK,
)


class GitCapability:
    """Trusted Git capability — structured repository operations.

    Discoverable through ``CapabilityRegistry`` under id ``git``.
    Intelligence never constructs shell commands; callers submit structured
    operations through the Capability Execution Engine. CLI details remain
    private to this package.
    """

    def __init__(self, config: GitCapabilityConfig) -> None:
        self._config = config

    @property
    def config(self) -> GitCapabilityConfig:
        return self._config

    def supported_operations(self) -> frozenset[str]:
        return _ALL_OPERATIONS

    def metadata(self) -> CapabilityMetadata:
        return CapabilityMetadata(
            id=CAPABILITY_ID,
            description=(
                "Root-scoped Git repository operations with structured status, "
                "branch, commit, diff, and remote results. Permissions separate "
                "read, local modify, and network operations."
            ),
            permissions=_GIT_PERMISSIONS,
            parameters=(
                CapabilityParameter(
                    name="operation",
                    type="string",
                    description=(
                        "Git operation name (status, list_branches, commit, "
                        "diff, fetch, push, …)."
                    ),
                ),
                CapabilityParameter(
                    name="repository",
                    type="string",
                    description="Path to a git worktree under an allowed root.",
                ),
                CapabilityParameter(
                    name="paths",
                    type="array",
                    description="File paths for stage/unstage operations.",
                    required=False,
                ),
                CapabilityParameter(
                    name="message",
                    type="string",
                    description="Commit message.",
                    required=False,
                ),
                CapabilityParameter(
                    name="branch",
                    type="string",
                    description="Branch name for checkout/create/pull/push.",
                    required=False,
                ),
                CapabilityParameter(
                    name="name",
                    type="string",
                    description="Branch name for create_branch.",
                    required=False,
                ),
                CapabilityParameter(
                    name="start_point",
                    type="string",
                    description="Optional start point for create_branch.",
                    required=False,
                ),
                CapabilityParameter(
                    name="checkout",
                    type="boolean",
                    description="Whether create_branch should also check out the branch.",
                    required=False,
                ),
                CapabilityParameter(
                    name="path",
                    type="string",
                    description="Optional path filter for diff.",
                    required=False,
                ),
                CapabilityParameter(
                    name="staged",
                    type="boolean",
                    description="When true, diff uses the staged index.",
                    required=False,
                ),
                CapabilityParameter(
                    name="include_ignored",
                    type="boolean",
                    description="Include ignored files in status.",
                    required=False,
                ),
                CapabilityParameter(
                    name="limit",
                    type="integer",
                    description="Max commits for commit_history.",
                    required=False,
                ),
                CapabilityParameter(
                    name="ref",
                    type="string",
                    description="Optional ref for commit_history.",
                    required=False,
                ),
                CapabilityParameter(
                    name="remote",
                    type="string",
                    description="Remote name for fetch/pull/push.",
                    required=False,
                ),
                CapabilityParameter(
                    name="set_upstream",
                    type="boolean",
                    description="Set upstream when pushing.",
                    required=False,
                ),
                CapabilityParameter(
                    name="allow_empty",
                    type="boolean",
                    description="Allow empty commits.",
                    required=False,
                ),
                CapabilityParameter(
                    name="timeout_seconds",
                    type="number",
                    description="Per-operation timeout capped by configuration.",
                    required=False,
                ),
            ),
        )

    def execute(self, request: CapabilityRequest, context: CapabilityContext) -> object:
        context.check_cancelled()
        operation = _require_string(request.arguments, "operation")
        permission = _permission_for_operation(operation)
        if not context.has_permission(permission):
            raise CapabilityExecutionError(
                f"Missing required permission '{permission}'.",
                code=PERMISSION_DENIED,
                details={
                    "permission": permission.name,
                    "operation": operation,
                },
            )
        if operation not in _ALL_OPERATIONS:
            raise CapabilityExecutionError(
                f"Unsupported git operation '{operation}'.",
                code=UNSUPPORTED_OPERATION,
                details={"operation": operation},
            )

        repository = resolve_repository_path(
            request.arguments.get("repository"),
            allowed_roots=self._config.allowed_roots,
        )
        timeout_seconds = _resolve_timeout(request.arguments, self._config)
        context.check_cancelled()

        if operation == "detect_repository":
            return operations.detect_repository(
                repository,
                config=self._config,
                timeout_seconds=timeout_seconds,
                cancellation=context.cancellation,
            )
        if operation == "repository_info":
            return operations.repository_info(
                repository,
                config=self._config,
                timeout_seconds=timeout_seconds,
                cancellation=context.cancellation,
            )
        if operation == "status":
            return operations.status(
                repository,
                config=self._config,
                timeout_seconds=timeout_seconds,
                cancellation=context.cancellation,
                include_ignored=_optional_bool(request.arguments, "include_ignored", False),
            )
        if operation == "list_branches":
            return operations.list_branches(
                repository,
                config=self._config,
                timeout_seconds=timeout_seconds,
                cancellation=context.cancellation,
            )
        if operation == "checkout_branch":
            return operations.checkout_branch(
                repository,
                branch=_require_string(request.arguments, "branch"),
                config=self._config,
                timeout_seconds=timeout_seconds,
                cancellation=context.cancellation,
            )
        if operation == "create_branch":
            return operations.create_branch(
                repository,
                name=_require_string(request.arguments, "name"),
                start_point=_optional_string(request.arguments, "start_point"),
                checkout=_optional_bool(request.arguments, "checkout", False),
                config=self._config,
                timeout_seconds=timeout_seconds,
                cancellation=context.cancellation,
            )
        if operation == "stage_files":
            return operations.stage_files(
                repository,
                paths=_require_paths_arg(request.arguments),
                config=self._config,
                timeout_seconds=timeout_seconds,
                cancellation=context.cancellation,
            )
        if operation == "unstage_files":
            return operations.unstage_files(
                repository,
                paths=_require_paths_arg(request.arguments),
                config=self._config,
                timeout_seconds=timeout_seconds,
                cancellation=context.cancellation,
            )
        if operation == "commit":
            return operations.commit(
                repository,
                message=_require_string(request.arguments, "message"),
                config=self._config,
                timeout_seconds=timeout_seconds,
                cancellation=context.cancellation,
                allow_empty=_optional_bool(request.arguments, "allow_empty", False),
            )
        if operation == "commit_history":
            return operations.commit_history(
                repository,
                limit=_resolve_history_limit(request.arguments, self._config),
                ref=_optional_string(request.arguments, "ref"),
                config=self._config,
                timeout_seconds=timeout_seconds,
                cancellation=context.cancellation,
            )
        if operation == "fetch":
            return operations.fetch(
                repository,
                remote=_optional_string(request.arguments, "remote"),
                config=self._config,
                timeout_seconds=timeout_seconds,
                cancellation=context.cancellation,
            )
        if operation == "pull":
            return operations.pull(
                repository,
                remote=_optional_string(request.arguments, "remote"),
                branch=_optional_string(request.arguments, "branch"),
                config=self._config,
                timeout_seconds=timeout_seconds,
                cancellation=context.cancellation,
            )
        if operation == "push":
            return operations.push(
                repository,
                remote=_optional_string(request.arguments, "remote"),
                branch=_optional_string(request.arguments, "branch"),
                set_upstream=_optional_bool(request.arguments, "set_upstream", False),
                config=self._config,
                timeout_seconds=timeout_seconds,
                cancellation=context.cancellation,
            )
        if operation == "diff":
            return operations.diff(
                repository,
                path=_optional_string(request.arguments, "path"),
                staged=_optional_bool(request.arguments, "staged", False),
                config=self._config,
                timeout_seconds=timeout_seconds,
                cancellation=context.cancellation,
            )

        raise CapabilityExecutionError(
            f"Unsupported git operation '{operation}'.",
            code=UNSUPPORTED_OPERATION,
            details={"operation": operation},
        )


def register_git_capability(
    registry: CapabilityRegistry,
    config: GitCapabilityConfig,
) -> GitCapability:
    """Register the Git Capability on a CapabilityRegistry."""
    capability = GitCapability(config)
    registry.register(capability)
    return capability


def _permission_for_operation(operation: str) -> CapabilityPermission:
    if operation in READ_OPERATIONS:
        return GIT_READ
    if operation in WRITE_OPERATIONS:
        return GIT_WRITE
    if operation in NETWORK_OPERATIONS:
        return GIT_NETWORK
    return GIT_READ


def _require_string(arguments: Mapping[str, object], name: str) -> str:
    value = arguments.get(name)
    if not isinstance(value, str) or not value.strip():
        code = UNSUPPORTED_OPERATION
        if name == "repository":
            code = INVALID_REPOSITORY
        elif name == "message":
            code = EMPTY_MESSAGE
        elif name in {"branch", "name", "ref", "remote", "start_point"}:
            code = INVALID_REF
        raise CapabilityExecutionError(
            f"Argument '{name}' must be a non-empty string.",
            code=code,
            details={"argument": name},
        )
    return value.strip()


def _optional_string(arguments: Mapping[str, object], name: str) -> str | None:
    if name not in arguments:
        return None
    value = arguments[name]
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise CapabilityExecutionError(
            f"Argument '{name}' must be a non-empty string when provided.",
            code=UNSUPPORTED_OPERATION,
            details={"argument": name},
        )
    return value.strip()


def _optional_bool(arguments: Mapping[str, object], name: str, default: bool) -> bool:
    if name not in arguments:
        return default
    value = arguments[name]
    if not isinstance(value, bool):
        raise CapabilityExecutionError(
            f"Argument '{name}' must be a boolean.",
            code=UNSUPPORTED_OPERATION,
            details={"argument": name},
        )
    return value


def _require_paths_arg(arguments: Mapping[str, object]) -> list[str]:
    value = arguments.get("paths")
    if not isinstance(value, (list, tuple)):
        raise CapabilityExecutionError(
            "Argument 'paths' must be an array of strings.",
            code=UNSUPPORTED_OPERATION,
            details={"argument": "paths"},
        )
    return list(value)


def _resolve_timeout(
    arguments: Mapping[str, object],
    config: GitCapabilityConfig,
) -> float:
    if "timeout_seconds" not in arguments:
        return config.default_timeout_seconds
    value = arguments["timeout_seconds"]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise CapabilityExecutionError(
            "Argument 'timeout_seconds' must be a positive number.",
            code=INVALID_TIMEOUT,
            details={"argument": "timeout_seconds"},
        )
    timeout = float(value)
    if timeout <= 0:
        raise CapabilityExecutionError(
            "Argument 'timeout_seconds' must be a positive number.",
            code=INVALID_TIMEOUT,
            details={"argument": "timeout_seconds", "timeout_seconds": timeout},
        )
    return min(timeout, config.max_timeout_seconds)


def _resolve_history_limit(
    arguments: Mapping[str, object],
    config: GitCapabilityConfig,
) -> int:
    if "limit" not in arguments:
        return config.default_history_limit
    value = arguments["limit"]
    if isinstance(value, bool) or not isinstance(value, int):
        raise CapabilityExecutionError(
            "Argument 'limit' must be a positive integer.",
            code=UNSUPPORTED_OPERATION,
            details={"argument": "limit"},
        )
    if value <= 0:
        raise CapabilityExecutionError(
            "Argument 'limit' must be a positive integer.",
            code=UNSUPPORTED_OPERATION,
            details={"argument": "limit", "limit": value},
        )
    return min(value, config.max_history_limit)
