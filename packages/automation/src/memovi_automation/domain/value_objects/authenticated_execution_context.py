from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

from memovi_shared import WorkspaceId

from memovi_automation.domain.exceptions import InvalidCapabilityError
from memovi_automation.domain.value_objects.cancellation_token import CancellationToken


@dataclass(frozen=True, slots=True)
class AuthenticatedExecutionContext:
    """Server-owned identity and authorization context for capability execution.

    Capabilities never receive unauthenticated context. Clients may request
    actions; only the Authorization Service populates this object.
    """

    user_id: str
    workspace_id: WorkspaceId
    session_id: str
    request_id: str
    effective_permissions: frozenset[str]
    cancellation: CancellationToken = field(default_factory=CancellationToken)
    conversation_id: str | None = None
    correlation_id: str | None = None
    source: str = "api"
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        user_id = self.user_id.strip()
        session_id = self.session_id.strip()
        request_id = self.request_id.strip()
        if not user_id:
            raise InvalidCapabilityError("Authenticated execution context requires user_id.")
        if not session_id:
            raise InvalidCapabilityError("Authenticated execution context requires session_id.")
        if not request_id:
            raise InvalidCapabilityError("Authenticated execution context requires request_id.")
        if not isinstance(self.workspace_id, WorkspaceId):
            raise InvalidCapabilityError(
                "Authenticated execution context workspace_id must be a WorkspaceId.",
            )
        if not isinstance(self.cancellation, CancellationToken):
            raise InvalidCapabilityError(
                "Authenticated execution context cancellation must be a CancellationToken.",
            )
        if not isinstance(self.effective_permissions, frozenset):
            raise InvalidCapabilityError(
                "Authenticated execution context effective_permissions must be a frozenset.",
            )
        source = self.source.strip() or "api"
        object.__setattr__(self, "user_id", user_id)
        object.__setattr__(self, "session_id", session_id)
        object.__setattr__(self, "request_id", request_id)
        object.__setattr__(self, "source", source)
        if self.conversation_id is not None:
            conversation_id = self.conversation_id.strip()
            if not conversation_id:
                raise InvalidCapabilityError(
                    "conversation_id cannot be blank when provided.",
                )
            object.__setattr__(self, "conversation_id", conversation_id)
        if self.correlation_id is not None:
            correlation_id = self.correlation_id.strip()
            if not correlation_id:
                raise InvalidCapabilityError(
                    "correlation_id cannot be blank when provided.",
                )
            object.__setattr__(self, "correlation_id", correlation_id)
        if not isinstance(self.metadata, Mapping):
            raise InvalidCapabilityError(
                "Authenticated execution context metadata must be a mapping.",
            )
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))

    def is_cancelled(self) -> bool:
        return self.cancellation.is_cancelled

    def has_permission(self, permission: str) -> bool:
        return permission in self.effective_permissions

    def with_effective_permissions(
        self,
        permissions: frozenset[str],
    ) -> AuthenticatedExecutionContext:
        return AuthenticatedExecutionContext(
            user_id=self.user_id,
            workspace_id=self.workspace_id,
            session_id=self.session_id,
            request_id=self.request_id,
            effective_permissions=permissions,
            cancellation=self.cancellation,
            conversation_id=self.conversation_id,
            correlation_id=self.correlation_id,
            source=self.source,
            metadata=dict(self.metadata),
        )

    @classmethod
    def create(
        cls,
        *,
        user_id: str,
        workspace_id: WorkspaceId,
        session_id: str,
        request_id: str,
        effective_permissions: frozenset[str] | None = None,
        cancellation: CancellationToken | None = None,
        conversation_id: str | None = None,
        correlation_id: str | None = None,
        source: str = "api",
        metadata: Mapping[str, object] | None = None,
    ) -> AuthenticatedExecutionContext:
        return cls(
            user_id=user_id,
            workspace_id=workspace_id,
            session_id=session_id,
            request_id=request_id,
            effective_permissions=(
                frozenset() if effective_permissions is None else frozenset(effective_permissions)
            ),
            cancellation=CancellationToken() if cancellation is None else cancellation,
            conversation_id=conversation_id,
            correlation_id=correlation_id,
            source=source,
            metadata={} if metadata is None else metadata,
        )
