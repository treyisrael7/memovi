"""Acceptance checklist for Capability Planner.

1. Intelligence generates execution plans (via CapabilityPlanner).
2. Execution plans are validated before use.
3. Plans execute through the Capability Execution Engine.
4. No capability is executed directly by the planner.
11. Multi-step Browser + Filesystem plan produces correct ordered steps.
12. Invalid plans are rejected before execution begins.
13. Execution still occurs exclusively through the Capability Execution Engine.
14. Planner output is deterministic for identical requests.
15. Full regression suite (run separately).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from memovi_automation.testing import make_auth_context
from memovi_automation import (
    BrowserCapabilityConfig,
    CapabilityExecutionEngine,
    CapabilityInvoker,
    CapabilityPlanner,
    CapabilityRegistry,
    FilesystemCapabilityConfig,
    InMemoryExecutionAuditStore,
    InMemoryPermissionPolicyStore,
    InvalidExecutionPlanError,
    PermissionMode,
    PlanExecutionService,
    register_browser_capability,
    register_filesystem_capability,
)
from memovi_automation.browser import FetchResult, ProviderSearchResults, SearchHit
from memovi_automation.browser.config import BrowserCapabilityConfig as BrowserConfig
from memovi_shared import WorkspaceId


class FakeBrowserProvider:
    def __init__(self) -> None:
        self.fetch_calls = 0
        self.search_calls = 0
        self.download_calls = 0

    def fetch(self, url, *, config: BrowserConfig, timeout_seconds, cancellation=None, on_progress=None):
        self.fetch_calls += 1
        html = (
            "<html><head><title>Planned Page</title>"
            "<meta name='description' content='from plan'></head>"
            "<body><p>Readable planned content.</p></body></html>"
        )
        return FetchResult(
            url=url,
            final_url=url,
            status_code=200,
            content_type="text/html",
            body=html.encode("utf-8"),
        )

    def search(self, query, *, limit, config: BrowserConfig, timeout_seconds, cancellation=None):
        self.search_calls += 1
        return ProviderSearchResults(
            query=query,
            results=(
                SearchHit(
                    title="Result",
                    url="https://example.com/page",
                    snippet="snippet",
                ),
            )[:limit],
        )

    def download_bytes(
        self, url, *, config: BrowserConfig, timeout_seconds, cancellation=None, on_progress=None
    ):
        self.download_calls += 1
        return FetchResult(
            url=url,
            final_url=url,
            status_code=200,
            content_type="text/plain",
            body=b"downloaded-via-plan",
        )


def _stack(
    root: Path,
    *,
    mode: PermissionMode = PermissionMode.ALWAYS_ALLOW,
    with_browser: bool = False,
):
    registry = CapabilityRegistry()
    register_filesystem_capability(
        registry,
        FilesystemCapabilityConfig.from_roots([root]),
    )
    provider = FakeBrowserProvider() if with_browser else None
    if with_browser:
        register_browser_capability(
            registry,
            BrowserCapabilityConfig.from_roots([root]),
            provider=provider,
        )
    planner = CapabilityPlanner(registry=registry)
    policies = InMemoryPermissionPolicyStore(default_mode=mode)
    policies.set("filesystem", mode, workspace_id=WorkspaceId.default())
    if with_browser:
        policies.set("browser", mode, workspace_id=WorkspaceId.default())
    engine = CapabilityExecutionEngine(
        registry=registry,
        invoker=CapabilityInvoker(registry=registry),
        permission_policies=policies,
        audit_store=InMemoryExecutionAuditStore(),
        default_permission_mode=mode,
    )
    return planner, PlanExecutionService(engine=engine, planner=planner), engine, provider


def _browser_filesystem_steps() -> list[dict[str, object]]:
    return [
        {
            "step_id": "search",
            "capability_id": "browser",
            "operation": "search_web",
            "arguments": {"query": "memovi planner", "limit": 1},
            "expected_result": "SearchResults",
        },
        {
            "step_id": "open",
            "capability_id": "browser",
            "operation": "open_url",
            "arguments": {"url": "https://example.com/page"},
            "dependencies": ["search"],
            "expected_result": "NavigationResult",
        },
        {
            "step_id": "extract",
            "capability_id": "browser",
            "operation": "extract_content",
            "arguments": {"url": "https://example.com/page"},
            "dependencies": ["open"],
            "expected_result": "ExtractedContent",
        },
        {
            "step_id": "save",
            "capability_id": "browser",
            "operation": "download_file",
            "arguments": {
                "url": "https://example.com/page.txt",
                "destination": "inbox/page.txt",
            },
            "dependencies": ["extract"],
            "expected_result": "DownloadResult",
        },
        {
            "step_id": "verify",
            "capability_id": "filesystem",
            "operation": "exists",
            "arguments": {"path": "inbox/page.txt"},
            "dependencies": ["save"],
            "expected_result": "FilesystemExists",
        },
    ]


def test_1_intelligence_generates_execution_plans(tmp_path: Path) -> None:
    root = tmp_path / "ws"
    root.mkdir()
    (root / "a.txt").write_text("a", encoding="utf-8")
    planner, _service, _engine, _provider = _stack(root)

    plan = planner.create_plan(
        workspace_id=WorkspaceId.default(),
        goal="Search then open then extract (filesystem analog)",
        steps=[
            {
                "step_id": "exists",
                "capability_id": "filesystem",
                "operation": "exists",
                "arguments": {"path": "a.txt"},
            },
            {
                "step_id": "read",
                "capability_id": "filesystem",
                "operation": "read_file",
                "arguments": {"path": "a.txt"},
                "dependencies": ["exists"],
                "expected_result": "ExtractedContent",
            },
        ],
        conversation_id="conv-1",
        correlation_id="corr-1",
    )

    assert plan.plan_id
    assert plan.workspace_id == WorkspaceId.default().value
    assert plan.estimated_execution_count == 2
    assert plan.required_capabilities == ("filesystem",)
    assert [step.operation for step in plan.steps] == ["exists", "read_file"]
    assert plan.conversation_id == "conv-1"


def test_2_execution_plans_are_validated(tmp_path: Path) -> None:
    root = tmp_path / "ws"
    root.mkdir()
    planner, _service, _engine, _provider = _stack(root)

    with pytest.raises(InvalidExecutionPlanError) as exc:
        planner.create_plan(
            workspace_id=WorkspaceId.default(),
            goal="Invalid",
            steps=[
                {
                    "capability_id": "filesystem",
                    "operation": "not_a_real_op",
                    "arguments": {"path": "x"},
                }
            ],
        )
    assert exc.value.code == "unknown_operation"


def test_3_plans_execute_through_capability_execution_engine(tmp_path: Path) -> None:
    root = tmp_path / "ws"
    root.mkdir()
    (root / "notes.txt").write_text("planned", encoding="utf-8")
    planner, service, engine, _provider = _stack(root)

    plan = planner.create_plan(
        workspace_id=WorkspaceId.default(),
        goal="Read notes through engine",
        steps=[
            {
                "step_id": "read",
                "capability_id": "filesystem",
                "operation": "read_file",
                "arguments": {"path": "notes.txt"},
            }
        ],
    )
    result = service.execute_plan(plan, context=make_auth_context())
    assert result.status == "completed"
    assert result.step_results[0].output["content"] == "planned"

    executions = engine.list_executions(workspace_id=WorkspaceId.default())
    assert any(item.execution_id == result.step_results[0].execution_id for item in executions)
    matched = next(
        item for item in executions if item.execution_id == result.step_results[0].execution_id
    )
    assert matched.metadata.get("plan_id") == plan.plan_id
    assert matched.metadata.get("step_id") == "read"


def test_4_planner_does_not_execute_capabilities(tmp_path: Path) -> None:
    root = tmp_path / "ws"
    root.mkdir()
    target = root / "untouched.txt"
    target.write_text("safe", encoding="utf-8")
    planner, _service, engine, provider = _stack(root, with_browser=True)

    planner.create_plan(
        workspace_id=WorkspaceId.default(),
        goal="Planning only",
        steps=_browser_filesystem_steps(),
    )

    assert target.read_text(encoding="utf-8") == "safe"
    assert engine.list_executions(workspace_id=WorkspaceId.default()) == ()
    assert provider is not None
    assert provider.fetch_calls == 0
    assert provider.search_calls == 0
    assert provider.download_calls == 0
    assert not (root / "inbox" / "page.txt").exists()


def test_11_multi_step_browser_filesystem_plan_order(tmp_path: Path) -> None:
    root = tmp_path / "ws"
    root.mkdir()
    planner, _service, _engine, _provider = _stack(root, with_browser=True)

    plan = planner.create_plan(
        workspace_id=WorkspaceId.default(),
        goal="I need to search, then open a page, then extract its contents, then save.",
        steps=_browser_filesystem_steps(),
    )

    assert [step.step_id for step in plan.steps] == [
        "search",
        "open",
        "extract",
        "save",
        "verify",
    ]
    assert [step.capability_id for step in plan.steps] == [
        "browser",
        "browser",
        "browser",
        "browser",
        "filesystem",
    ]
    assert [step.operation for step in plan.steps] == [
        "search_web",
        "open_url",
        "extract_content",
        "download_file",
        "exists",
    ]
    assert plan.required_capabilities == ("browser", "filesystem")
    assert plan.estimated_execution_count == 5
    assert plan.dependencies == (
        ("search", "open"),
        ("open", "extract"),
        ("extract", "save"),
        ("save", "verify"),
    )
    assert plan.steps[1].dependency_step_ids == ("search",)
    assert plan.steps[4].dependency_step_ids == ("save",)


def test_12_invalid_plans_rejected_before_execution(tmp_path: Path) -> None:
    root = tmp_path / "ws"
    root.mkdir()
    planner, service, engine, provider = _stack(root, with_browser=True)

    invalid_cases = [
        (
            "unknown_capability",
            [
                {
                    "capability_id": "clipboard",
                    "operation": "read",
                    "arguments": {},
                }
            ],
        ),
        (
            "unknown_operation",
            [
                {
                    "capability_id": "browser",
                    "operation": "click_element",
                    "arguments": {"url": "https://example.com/"},
                }
            ],
        ),
        (
            "invalid_arguments",
            [
                {
                    "capability_id": "filesystem",
                    "operation": "read_file",
                    "arguments": {},
                }
            ],
        ),
        (
            "invalid_dependency_order",
            [
                {
                    "step_id": "later",
                    "capability_id": "filesystem",
                    "operation": "exists",
                    "arguments": {"path": "x"},
                    "dependencies": ["earlier"],
                },
                {
                    "step_id": "earlier",
                    "capability_id": "filesystem",
                    "operation": "exists",
                    "arguments": {"path": "x"},
                },
            ],
        ),
    ]

    for code, steps in invalid_cases:
        with pytest.raises(InvalidExecutionPlanError) as exc:
            planner.create_plan(
                workspace_id=WorkspaceId.default(),
                goal=f"Reject {code}",
                steps=steps,
            )
        assert exc.value.code == code

    # Nothing reached the engine or browser provider.
    assert engine.list_executions(workspace_id=WorkspaceId.default()) == ()
    assert provider is not None
    assert provider.fetch_calls == provider.search_calls == provider.download_calls == 0

    # execute_plan re-validates and refuses invalid plans before any submit.
    with pytest.raises(InvalidExecutionPlanError) as exec_exc:
        planner.create_plan(
            workspace_id=WorkspaceId.default(),
            goal="still invalid",
            steps=[
                {
                    "capability_id": "browser",
                    "operation": "click_element",
                    "arguments": {"url": "https://example.com/"},
                }
            ],
        )
    assert exec_exc.value.code == "unknown_operation"
    assert engine.list_executions(workspace_id=WorkspaceId.default()) == ()
    # Keep service referenced so the execute path stays in the acceptance surface.
    assert service.engine is engine


def test_13_execution_exclusively_through_engine(tmp_path: Path) -> None:
    root = tmp_path / "ws"
    root.mkdir()
    planner, service, engine, provider = _stack(root, with_browser=True)

    plan = planner.create_plan(
        workspace_id=WorkspaceId.default(),
        goal="Execute browser+filesystem via engine only",
        steps=_browser_filesystem_steps(),
    )
    # Planning alone does not touch providers.
    assert provider is not None
    assert provider.search_calls == 0

    result = service.execute_plan(plan, context=make_auth_context())
    assert result.status == "completed"
    assert len(result.step_results) == 5
    assert [step.status for step in result.step_results] == ["completed"] * 5

    executions = engine.list_executions(workspace_id=WorkspaceId.default())
    assert len(executions) == 5
    for step_result in result.step_results:
        match = next(item for item in executions if item.execution_id == step_result.execution_id)
        assert match.metadata.get("plan_id") == plan.plan_id
        assert match.metadata.get("step_id") == step_result.step_id
        assert match.metadata.get("source") == "capability_planner"
        # Engine owns the execution record.
        assert match.capability_id in {"browser", "filesystem"}

    assert provider.search_calls == 1
    assert provider.fetch_calls >= 2  # open + extract
    assert provider.download_calls == 1
    assert (root / "inbox" / "page.txt").exists()

    # Filesystem step visible through the same engine.
    verify = next(item for item in result.step_results if item.step_id == "verify")
    assert verify.output["exists"] is True


def test_14_planner_output_deterministic_for_identical_requests(tmp_path: Path) -> None:
    root = tmp_path / "ws"
    root.mkdir()
    planner, _service, _engine, _provider = _stack(root, with_browser=True)

    kwargs = {
        "workspace_id": WorkspaceId.default(),
        "goal": "Deterministic search → open → extract → save → verify",
        "steps": _browser_filesystem_steps(),
        "conversation_id": "conv-deterministic",
        "correlation_id": "corr-deterministic",
        "metadata": {"source": "acceptance"},
    }
    first = planner.create_plan(**kwargs)
    second = planner.create_plan(**kwargs)

    assert first.plan_id == second.plan_id
    assert first.workspace_id == second.workspace_id
    assert first.goal == second.goal
    assert first.required_capabilities == second.required_capabilities
    assert first.dependencies == second.dependencies
    assert first.estimated_execution_count == second.estimated_execution_count
    assert first.conversation_id == second.conversation_id
    assert first.correlation_id == second.correlation_id
    assert dict(first.metadata) == dict(second.metadata)
    assert first.step_ids == second.step_ids
    for left, right in zip(first.steps, second.steps, strict=True):
        assert left.step_id == right.step_id
        assert left.capability_id == right.capability_id
        assert left.operation == right.operation
        assert dict(left.arguments) == dict(right.arguments)
        assert left.dependency_step_ids == right.dependency_step_ids
        assert left.expected_result == right.expected_result

    # Different content yields a different deterministic plan id.
    different = planner.create_plan(
        workspace_id=WorkspaceId.default(),
        goal="Slightly different goal",
        steps=_browser_filesystem_steps(),
        conversation_id="conv-deterministic",
        correlation_id="corr-deterministic",
        metadata={"source": "acceptance"},
    )
    assert different.plan_id != first.plan_id
