"""Milestone 21 acceptance verification for the Capability Execution Engine.

Covers discovery, mock/filesystem execution, conversation handoff, Ask/Deny
permission modes, audit generation, and structured results.
"""

from __future__ import annotations

from pathlib import Path

from api.capability_execution_integration import CapabilityExecutionEngineAdapter
from memovi_automation import (
    FILESYSTEM_READ,
    CapabilityContext,
    CapabilityExecutionEngine,
    CapabilityExecutionRequest,
    CapabilityExecutionStatus,
    CapabilityInvoker,
    CapabilityMetadata,
    CapabilityParameter,
    CapabilityRegistry,
    CapabilityRequest,
    FilesystemCapabilityConfig,
    InMemoryExecutionAuditStore,
    InMemoryPermissionPolicyStore,
    PermissionMode,
    register_filesystem_capability,
)
from memovi_intelligence.application.commands.request_capability_execution import (
    RequestCapabilityExecution,
    RequestCapabilityExecutionCommand,
)
from memovi_intelligence.application.services import ConversationService
from memovi_intelligence.infrastructure import InMemoryConversationRepository
from memovi_shared import WorkspaceId


class MockReadOnlyCapability:
    """Read-only mock capability used for execution-engine acceptance checks."""

    def metadata(self) -> CapabilityMetadata:
        return CapabilityMetadata(
            id="mock.readonly",
            description="Read-only mock capability for execution engine verification.",
            permissions=(FILESYSTEM_READ,),
            parameters=(
                CapabilityParameter(
                    name="query",
                    type="string",
                    description="Lookup query.",
                ),
            ),
        )

    def execute(self, request: CapabilityRequest, context: CapabilityContext) -> object:
        context.check_cancelled()
        if not context.has_permission(FILESYSTEM_READ):
            raise RuntimeError("missing permission")
        return {
            "capability": "mock.readonly",
            "query": str(request.arguments["query"]),
            "result": "structured-mock-payload",
            "workspace_id": context.workspace_id.value,
        }


def _build_engine(
    *,
    mode: PermissionMode,
    tmp_path: Path | None = None,
    include_filesystem: bool = False,
) -> CapabilityExecutionEngine:
    registry = CapabilityRegistry()
    registry.register(MockReadOnlyCapability())
    if include_filesystem:
        assert tmp_path is not None
        register_filesystem_capability(
            registry,
            FilesystemCapabilityConfig.from_roots([tmp_path]),
        )

    policies = InMemoryPermissionPolicyStore(default_mode=mode)
    policies.set("mock.readonly", mode, workspace_id=WorkspaceId.default())
    if include_filesystem:
        policies.set("filesystem", mode, workspace_id=WorkspaceId.default())

    return CapabilityExecutionEngine(
        registry=registry,
        invoker=CapabilityInvoker(registry=registry),
        permission_policies=policies,
        audit_store=InMemoryExecutionAuditStore(),
        default_permission_mode=mode,
    )


def test_1_mock_capability_is_discoverable_by_execution_engine() -> None:
    engine = _build_engine(mode=PermissionMode.ALWAYS_ALLOW)

    assert engine.registry.contains("mock.readonly")
    metadata = engine.registry.metadata("mock.readonly")
    assert metadata.id == "mock.readonly"
    assert "query" in metadata.parameter_map()
    assert FILESYSTEM_READ in metadata.permissions

    listed = {item.id for item in engine.registry.list()}
    assert "mock.readonly" in listed


def test_2_readonly_mock_capability_returns_structured_success() -> None:
    engine = _build_engine(mode=PermissionMode.ALWAYS_ALLOW)

    result = engine.submit(
        CapabilityExecutionRequest.create(
            capability_id="mock.readonly",
            workspace_id=WorkspaceId.default(),
            arguments={"query": "memovi"},
            source="test",
        )
    )

    assert result.status is CapabilityExecutionStatus.COMPLETED
    assert result.error is None
    assert isinstance(result.output, dict)
    assert result.output["capability"] == "mock.readonly"
    assert result.output["query"] == "memovi"
    assert result.output["result"] == "structured-mock-payload"
    assert result.duration >= 0


def test_3_filesystem_result_is_returned_to_conversation(tmp_path: Path) -> None:
    note = tmp_path / "conversation-note.txt"
    note.write_text("conversation filesystem payload", encoding="utf-8")

    engine = _build_engine(
        mode=PermissionMode.ALWAYS_ALLOW,
        tmp_path=tmp_path,
        include_filesystem=True,
    )
    conversations = ConversationService(repository=InMemoryConversationRepository())
    conversation = conversations.create_conversation(workspace_id=WorkspaceId.default())
    use_case = RequestCapabilityExecution(
        conversations=conversations,
        capability_execution=CapabilityExecutionEngineAdapter(engine),
    )

    result = use_case.execute(
        RequestCapabilityExecutionCommand(
            workspace_id=WorkspaceId.default(),
            conversation_id=conversation.id.value,
            capability_id="filesystem",
            arguments={
                "operation": "read_file",
                "path": str(note),
            },
            permission_mode="always_allow",
        )
    )

    assert result.status == "completed"
    assert result.conversation_id == conversation.id.value
    assert isinstance(result.output, dict)
    assert result.output["operation"] == "read_file"
    assert result.output["content"] == "conversation filesystem payload"

    listed = engine.list_executions(
        workspace_id=WorkspaceId.default(),
        conversation_id=conversation.id.value,
    )
    assert len(listed) == 1
    assert listed[0].execution_id == result.execution_id
    assert listed[0].output == result.output


def test_4_ask_every_time_pauses_until_approval() -> None:
    engine = _build_engine(mode=PermissionMode.ASK_EVERY_TIME)

    pending = engine.submit(
        CapabilityExecutionRequest.create(
            capability_id="mock.readonly",
            workspace_id=WorkspaceId.default(),
            arguments={"query": "awaiting"},
        )
    )
    assert pending.status is CapabilityExecutionStatus.PENDING_APPROVAL
    assert pending.output is None

    still_pending = engine.get(pending.execution_id, workspace_id=WorkspaceId.default())
    assert still_pending.status is CapabilityExecutionStatus.PENDING_APPROVAL

    approved = engine.approve(pending.execution_id, workspace_id=WorkspaceId.default())
    assert approved.status is CapabilityExecutionStatus.COMPLETED
    assert approved.output is not None
    assert approved.output["result"] == "structured-mock-payload"


def test_5_deny_blocks_with_structured_error() -> None:
    engine = _build_engine(mode=PermissionMode.DENY)

    result = engine.submit(
        CapabilityExecutionRequest.create(
            capability_id="mock.readonly",
            workspace_id=WorkspaceId.default(),
            arguments={"query": "blocked"},
        )
    )

    assert result.status is CapabilityExecutionStatus.FAILED
    assert result.output is None
    assert result.error is not None
    assert result.error.code == "permission_denied"
    assert "denied" in result.error.message.lower()
    assert result.error.details["permission_mode"] == PermissionMode.DENY.value


def test_6_successful_execution_creates_audit_entry() -> None:
    engine = _build_engine(mode=PermissionMode.ALWAYS_ALLOW)

    result = engine.submit(
        CapabilityExecutionRequest.create(
            capability_id="mock.readonly",
            workspace_id=WorkspaceId.default(),
            arguments={"query": "audit-me"},
            source="verification",
        )
    )
    assert result.status is CapabilityExecutionStatus.COMPLETED

    audit = engine.list_audit(workspace_id=WorkspaceId.default())
    completed_entries = [
        entry
        for entry in audit
        if entry.execution_id == result.execution_id
        and entry.status is CapabilityExecutionStatus.COMPLETED
    ]
    assert len(completed_entries) == 1
    entry = completed_entries[0]
    assert entry.capability_id == "mock.readonly"
    assert entry.workspace_id == WorkspaceId.default().value
    assert entry.arguments["query"] == "audit-me"
    assert entry.result_summary["status"] == "completed"
    assert entry.result_summary["success"] is True
    assert entry.source == "verification"
    assert entry.duration >= 0
