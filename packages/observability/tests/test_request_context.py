from memovi_shared import WorkspaceId

from memovi_observability import (
    RequestContext,
    bind_request_context,
    clear_request_context,
    get_request_context,
    update_request_context,
)


def test_request_context_create_generates_request_id() -> None:
    context = RequestContext.create()
    assert context.request_id
    assert context.workspace_id is None
    assert context.correlation_id is None
    assert context.principal is None


def test_bind_and_clear_request_context() -> None:
    workspace_id = WorkspaceId.default()
    context = RequestContext.create(
        request_id="req-1",
        workspace_id=workspace_id,
        correlation_id="corr-1",
    )
    token = bind_request_context(context)
    try:
        bound = get_request_context()
        assert bound is not None
        assert bound.request_id == "req-1"
        assert bound.workspace_id == workspace_id
        assert bound.correlation_id == "corr-1"
    finally:
        clear_request_context(token)

    assert get_request_context() is None


def test_update_request_context_sets_workspace_id() -> None:
    token = bind_request_context(RequestContext.create(request_id="req-2"))
    try:
        workspace_id = WorkspaceId.default()
        updated = update_request_context(workspace_id=workspace_id)
        assert updated is not None
        assert updated.workspace_id == workspace_id
        assert get_request_context() is not None
        assert get_request_context().request_id == "req-2"
    finally:
        clear_request_context(token)


def test_as_log_fields_includes_consistent_keys() -> None:
    fields = RequestContext.create(
        request_id="req-3",
        workspace_id=WorkspaceId.default(),
        correlation_id="corr-3",
    ).as_log_fields()
    assert fields["request_id"] == "req-3"
    assert fields["workspace_id"] == WorkspaceId.default().value
    assert fields["correlation_id"] == "corr-3"
