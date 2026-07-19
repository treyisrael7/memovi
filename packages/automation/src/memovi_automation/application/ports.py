from typing import Protocol

from memovi_automation.domain.value_objects import (
    CapabilityContext,
    CapabilityMetadata,
    CapabilityRequest,
)


class Capability(Protocol):
    """Executable capability that Intelligence can discover and invoke.

    Implementations must remain provider-agnostic and must not depend on HTTP,
    FastAPI, UI frameworks, or other application internals. Host services are
    accessed only through CapabilityContext and future context-attached ports.
    """

    def metadata(self) -> CapabilityMetadata:
        """Return immutable discovery metadata, including required permissions."""
        raise NotImplementedError

    def execute(self, request: CapabilityRequest, context: CapabilityContext) -> object:
        """Perform the capability work and return structured output.

        Implementations should honor context.check_cancelled() for cooperative
        cancellation. Unexpected failures should raise CapabilityExecutionError
        (or a subclass) with a stable error code when possible.
        """
        raise NotImplementedError
