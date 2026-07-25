class AutomationDomainError(Exception):
    """Base exception for automation / capability domain failures."""


class InvalidCapabilityError(AutomationDomainError):
    """Raised when a capability value object or registration violates constraints."""


class UnknownCapabilityError(AutomationDomainError):
    """Raised when a requested capability is not registered."""


class CapabilityExecutionNotFoundError(AutomationDomainError):
    """Raised when a capability execution id is unknown in the workspace."""


class InvalidCapabilityArgumentsError(AutomationDomainError):
    """Raised when capability arguments fail schema validation."""


class InvalidExecutionPlanError(AutomationDomainError):
    """Raised when an execution plan fails structural or schema validation."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "invalid_execution_plan",
        details: dict[str, object] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.details: dict[str, object] = {} if details is None else dict(details)


class InvalidWorkflowError(AutomationDomainError):
    """Raised when a workflow definition, variables, or mappings are invalid."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "invalid_workflow",
        details: dict[str, object] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.details: dict[str, object] = {} if details is None else dict(details)


class UnknownWorkflowError(AutomationDomainError):
    """Raised when a requested workflow id is not in the library."""

    def __init__(
        self,
        message: str,
        *,
        workflow_id: str | None = None,
    ) -> None:
        super().__init__(message)
        self.workflow_id = workflow_id


class CapabilityExecutionError(AutomationDomainError):
    """Raised when a capability fails during execution."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "execution_failed",
        details: dict[str, object] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.details: dict[str, object] = {} if details is None else dict(details)


class CapabilityTimeoutError(AutomationDomainError):
    """Raised when a capability exceeds its allotted execution time."""


class CapabilityCancelledError(AutomationDomainError):
    """Raised when a capability invocation is cancelled."""
