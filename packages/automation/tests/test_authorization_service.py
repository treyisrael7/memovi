"""Authorization Service and durable policy/audit store coverage."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from memovi_automation import (
    CapabilityExecutionEngine,
    CapabilityExecutionPolicy,
    CapabilityExecutionRequest,
    CapabilityExecutionStatus,
    CapabilityInvoker,
    CapabilityRegistry,
    FilesystemCapabilityConfig,
    InMemoryExecutionAuditStore,
    InMemoryPermissionPolicyStore,
    PermissionMode,
    register_filesystem_capability,
)
from memovi_automation.application.services.capability_authorization_service import (
    CapabilityAuthorizationService,
)
from memovi_automation.domain.exceptions import AuthorizationDeniedError
from memovi_automation.infrastructure.persistence import Base as AutomationBase
from memovi_automation.infrastructure.sqlalchemy_execution_audit_store import (
    SqlAlchemyExecutionAuditStore,
)
from memovi_automation.infrastructure.sqlalchemy_permission_policy_store import (
    SqlAlchemyPermissionPolicyStore,
)
from memovi_automation.testing import make_auth_context
from memovi_shared import WorkspaceId
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


class _Membership:
    def __init__(self, *, allowed: bool = True, role: str = "owner") -> None:
        self.allowed = allowed
        self.role = role

    def is_member(self, *, user_id: str, workspace_id: WorkspaceId) -> bool:
        return self.allowed

    def get_role(self, *, user_id: str, workspace_id: WorkspaceId) -> str | None:
        return self.role if self.allowed else None


def _registry(tmp_path: Path) -> CapabilityRegistry:
    registry = CapabilityRegistry()
    register_filesystem_capability(
        registry,
        FilesystemCapabilityConfig.from_roots([tmp_path]),
    )
    return registry


def test_authorization_service_denies_non_members(tmp_path: Path) -> None:
    registry = _registry(tmp_path)
    policies = InMemoryPermissionPolicyStore(default_mode=PermissionMode.ALWAYS_ALLOW)
    service = CapabilityAuthorizationService(
        membership=_Membership(allowed=False),
        permission_policies=policies,
        registry=registry,
    )
    with pytest.raises(AuthorizationDeniedError):
        service.authorize_capability(
            user_id="u1",
            session_id="s1",
            workspace_id=WorkspaceId.default(),
            request_id="r1",
            capability_id="filesystem",
        )


def test_authorization_service_uses_server_policy(tmp_path: Path) -> None:
    registry = _registry(tmp_path)
    policies = InMemoryPermissionPolicyStore(default_mode=PermissionMode.ASK_EVERY_TIME)
    policies.set("filesystem", PermissionMode.DENY, workspace_id=WorkspaceId.default())
    service = CapabilityAuthorizationService(
        membership=_Membership(allowed=True),
        permission_policies=policies,
        registry=registry,
    )
    _context, decision = service.authorize_capability(
        user_id="u1",
        session_id="s1",
        workspace_id=WorkspaceId.default(),
        request_id="r1",
        capability_id="filesystem",
    )
    assert decision.allowed is False
    assert decision.permission_mode is PermissionMode.DENY


def test_authorization_service_requires_owner(tmp_path: Path) -> None:
    registry = _registry(tmp_path)
    policies = InMemoryPermissionPolicyStore(default_mode=PermissionMode.ASK_EVERY_TIME)
    service = CapabilityAuthorizationService(
        membership=_Membership(allowed=True, role="member"),
        permission_policies=policies,
        registry=registry,
    )
    with pytest.raises(AuthorizationDeniedError) as exc:
        service.require_workspace_owner(
            user_id="u1",
            workspace_id=WorkspaceId.default(),
        )
    assert exc.value.code == "workspace_owner_required"


def test_engine_permission_mode_requires_owner(tmp_path: Path) -> None:
    registry = _registry(tmp_path)
    policies = InMemoryPermissionPolicyStore(default_mode=PermissionMode.ASK_EVERY_TIME)
    engine = CapabilityExecutionEngine(
        registry=registry,
        invoker=CapabilityInvoker(registry=registry),
        permission_policies=policies,
        audit_store=InMemoryExecutionAuditStore(),
        authorization=CapabilityAuthorizationService(
            membership=_Membership(allowed=True, role="member"),
            permission_policies=policies,
            registry=registry,
        ),
    )
    with pytest.raises(AuthorizationDeniedError):
        engine.set_permission_mode(
            "filesystem",
            PermissionMode.ALWAYS_ALLOW,
            workspace_id=WorkspaceId.default(),
            context=make_auth_context(),
        )


def test_engine_ignores_client_permission_mode(tmp_path: Path) -> None:
    registry = _registry(tmp_path)
    policies = InMemoryPermissionPolicyStore(default_mode=PermissionMode.DENY)
    policies.set("filesystem", PermissionMode.DENY, workspace_id=WorkspaceId.default())
    engine = CapabilityExecutionEngine(
        registry=registry,
        invoker=CapabilityInvoker(registry=registry),
        permission_policies=policies,
        audit_store=InMemoryExecutionAuditStore(),
        authorization=CapabilityAuthorizationService(
            membership=_Membership(allowed=True),
            permission_policies=policies,
            registry=registry,
        ),
        default_permission_mode=PermissionMode.DENY,
    )
    result = engine.submit(
        CapabilityExecutionRequest.create(
            capability_id="filesystem",
            workspace_id=WorkspaceId.default(),
            arguments={"operation": "exists", "path": str(tmp_path)},
            policy=CapabilityExecutionPolicy(permission_mode=PermissionMode.ALWAYS_ALLOW),
        ),
        make_auth_context(),
    )
    assert result.status is CapabilityExecutionStatus.FAILED
    assert result.error is not None
    assert result.error.code == "permission_denied"


def test_durable_policy_and_audit_survive_reload(tmp_path: Path) -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    AutomationBase.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)

    policy_store = SqlAlchemyPermissionPolicyStore(
        factory,
        default_mode=PermissionMode.ASK_EVERY_TIME,
    )
    policy_store.set(
        "filesystem",
        PermissionMode.ALWAYS_ALLOW,
        workspace_id=WorkspaceId.default(),
    )
    assert (
        SqlAlchemyPermissionPolicyStore(factory).get(
            "filesystem",
            workspace_id=WorkspaceId.default(),
        )
        is PermissionMode.ALWAYS_ALLOW
    )

    audit = SqlAlchemyExecutionAuditStore(factory)
    from memovi_automation.domain.value_objects.execution_audit_entry import (
        ExecutionAuditEntry,
    )

    entry = ExecutionAuditEntry(
        id=str(uuid4()),
        execution_id=str(uuid4()),
        workspace_id=WorkspaceId.default().value,
        capability_id="filesystem",
        status=CapabilityExecutionStatus.COMPLETED,
        permission_mode=PermissionMode.ALWAYS_ALLOW,
        arguments={"operation": "exists"},
        result_summary={"status": "completed", "operation": "exists", "success": True},
        duration=0.01,
        timestamp=datetime.now(UTC),
        user_id="user-1",
        operation="exists",
        source="test",
    )
    audit.append(entry)
    reloaded = SqlAlchemyExecutionAuditStore(factory).list_for_workspace(
        workspace_id=WorkspaceId.default(),
    )
    assert len(reloaded) == 1
    assert reloaded[0].user_id == "user-1"
    assert reloaded[0].operation == "exists"
    engine.dispose()
