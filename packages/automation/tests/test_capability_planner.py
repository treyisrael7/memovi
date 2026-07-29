"""Unit tests for CapabilityPlanner and ExecutionPlanValidator."""

from __future__ import annotations

from pathlib import Path

import pytest
from memovi_automation import (
    CapabilityExecutionEngine,
    CapabilityInvoker,
    CapabilityPlanner,
    CapabilityRegistry,
    ExecutionPlanValidator,
    FilesystemCapabilityConfig,
    InMemoryExecutionAuditStore,
    InMemoryPermissionPolicyStore,
    InvalidExecutionPlanError,
    PermissionMode,
    PlanExecutionService,
    register_filesystem_capability,
)
from memovi_automation.testing import make_auth_context
from memovi_shared import WorkspaceId


@pytest.fixture
def sandbox(tmp_path: Path) -> Path:
    root = tmp_path / "ws"
    root.mkdir()
    (root / "readme.txt").write_text("hello planner", encoding="utf-8")
    return root


def _registry(root: Path) -> CapabilityRegistry:
    registry = CapabilityRegistry()
    register_filesystem_capability(
        registry,
        FilesystemCapabilityConfig.from_roots([root]),
    )
    return registry


def test_create_plan_selects_capabilities_and_orders_steps(sandbox: Path) -> None:
    planner = CapabilityPlanner(registry=_registry(sandbox))
    plan = planner.create_plan(
        workspace_id=WorkspaceId.default(),
        goal="Read a file then check it exists",
        steps=[
            {
                "step_id": "read",
                "capability_id": "filesystem",
                "operation": "read_file",
                "arguments": {"path": "readme.txt"},
                "expected_result": "file contents",
            },
            {
                "step_id": "exists",
                "capability_id": "filesystem",
                "operation": "exists",
                "arguments": {"path": "readme.txt"},
                "dependencies": ["read"],
            },
        ],
    )
    assert plan.goal.startswith("Read a file")
    assert plan.required_capabilities == ("filesystem",)
    assert plan.estimated_execution_count == 2
    assert plan.steps[0].operation == "read_file"
    assert plan.steps[1].dependency_step_ids == ("read",)
    assert plan.dependencies == (("read", "exists"),)


def test_validator_rejects_unknown_capability(sandbox: Path) -> None:
    planner = CapabilityPlanner(registry=_registry(sandbox))
    with pytest.raises(InvalidExecutionPlanError) as exc:
        planner.create_plan(
            workspace_id=WorkspaceId.default(),
            goal="Use missing capability",
            steps=[
                {
                    "capability_id": "clipboard",
                    "operation": "read",
                    "arguments": {},
                }
            ],
        )
    assert exc.value.code == "unknown_capability"


def test_validator_rejects_unknown_operation(sandbox: Path) -> None:
    planner = CapabilityPlanner(registry=_registry(sandbox))
    with pytest.raises(InvalidExecutionPlanError) as exc:
        planner.create_plan(
            workspace_id=WorkspaceId.default(),
            goal="Bad op",
            steps=[
                {
                    "capability_id": "filesystem",
                    "operation": "format_disk",
                    "arguments": {"path": "readme.txt"},
                }
            ],
        )
    assert exc.value.code == "unknown_operation"


def test_validator_rejects_invalid_arguments(sandbox: Path) -> None:
    planner = CapabilityPlanner(registry=_registry(sandbox))
    with pytest.raises(InvalidExecutionPlanError) as exc:
        planner.create_plan(
            workspace_id=WorkspaceId.default(),
            goal="Missing path",
            steps=[
                {
                    "capability_id": "filesystem",
                    "operation": "read_file",
                    "arguments": {},
                }
            ],
        )
    assert exc.value.code == "invalid_arguments"


def test_validator_rejects_cyclic_dependency_order(sandbox: Path) -> None:
    planner = CapabilityPlanner(registry=_registry(sandbox))
    with pytest.raises(InvalidExecutionPlanError) as exc:
        planner.create_plan(
            workspace_id=WorkspaceId.default(),
            goal="Bad deps",
            steps=[
                {
                    "step_id": "a",
                    "capability_id": "filesystem",
                    "operation": "exists",
                    "arguments": {"path": "readme.txt"},
                    "dependencies": ["b"],
                },
                {
                    "step_id": "b",
                    "capability_id": "filesystem",
                    "operation": "exists",
                    "arguments": {"path": "readme.txt"},
                },
            ],
        )
    assert exc.value.code == "invalid_dependency_order"


def test_planner_never_executes_capabilities(sandbox: Path) -> None:
    registry = _registry(sandbox)
    planner = CapabilityPlanner(registry=registry)
    # Creating a plan must not touch files beyond registration.
    before = (sandbox / "readme.txt").read_text(encoding="utf-8")
    planner.create_plan(
        workspace_id=WorkspaceId.default(),
        goal="No side effects",
        steps=[
            {
                "capability_id": "filesystem",
                "operation": "read_file",
                "arguments": {"path": "readme.txt"},
            }
        ],
    )
    assert (sandbox / "readme.txt").read_text(encoding="utf-8") == before


def test_plan_executes_only_through_execution_engine(sandbox: Path) -> None:
    registry = _registry(sandbox)
    planner = CapabilityPlanner(registry=registry)
    policies = InMemoryPermissionPolicyStore(default_mode=PermissionMode.ALWAYS_ALLOW)
    policies.set("filesystem", PermissionMode.ALWAYS_ALLOW, workspace_id=WorkspaceId.default())
    engine = CapabilityExecutionEngine(
        registry=registry,
        invoker=CapabilityInvoker(registry=registry),
        permission_policies=policies,
        audit_store=InMemoryExecutionAuditStore(),
        default_permission_mode=PermissionMode.ALWAYS_ALLOW,
    )
    service = PlanExecutionService(engine=engine, planner=planner)

    plan = planner.create_plan(
        workspace_id=WorkspaceId.default(),
        goal="Read via plan",
        steps=[
            {
                "step_id": "read",
                "capability_id": "filesystem",
                "operation": "read_file",
                "arguments": {"path": "readme.txt"},
            }
        ],
    )
    result = service.execute_plan(plan, context=make_auth_context())
    assert result.status == "completed"
    assert len(result.step_results) == 1
    assert result.step_results[0].status == "completed"
    assert result.step_results[0].output["content"] == "hello planner"
    assert result.step_results[0].execution_id


def test_validate_plan_reuses_validator(sandbox: Path) -> None:
    registry = _registry(sandbox)
    validator = ExecutionPlanValidator(registry=registry)
    planner = CapabilityPlanner(registry=registry, validator=validator)
    plan = planner.create_plan(
        workspace_id=WorkspaceId.default(),
        goal="Validate again",
        steps=[
            {
                "capability_id": "filesystem",
                "operation": "exists",
                "arguments": {"path": "readme.txt"},
            }
        ],
    )
    assert planner.validate_plan(plan) is plan
