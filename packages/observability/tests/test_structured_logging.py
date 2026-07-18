import json
import logging

import pytest
from memovi_shared import WorkspaceId

from memovi_observability import (
    RequestContext,
    bind_request_context,
    clear_request_context,
    configure_structured_logging,
)
from memovi_observability.logging.structured import (
    JsonFormatter,
    RequestContextFilter,
    log_operation,
)


def test_json_formatter_includes_request_context_fields() -> None:
    configure_structured_logging()
    token = bind_request_context(
        RequestContext.create(
            request_id="req-log-1",
            workspace_id=WorkspaceId.default(),
        )
    )
    try:
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname=__file__,
            lineno=1,
            msg="hello",
            args=(),
            exc_info=None,
        )
        record.operation = "test.op"
        record.status = "success"
        record.duration_ms = 12.5
        RequestContextFilter().filter(record)
        payload = json.loads(JsonFormatter().format(record))
        assert payload["request_id"] == "req-log-1"
        assert payload["workspace_id"] == WorkspaceId.default().value
        assert payload["operation"] == "test.op"
        assert payload["status"] == "success"
        assert payload["duration_ms"] == 12.5
        assert payload["message"] == "hello"
    finally:
        clear_request_context(token)


def test_request_context_stamped_on_record_at_emit_time(
    caplog: pytest.LogCaptureFixture,
) -> None:
    token = bind_request_context(
        RequestContext.create(
            request_id="req-stamp-1",
            workspace_id=WorkspaceId.default(),
        )
    )
    try:
        logger = logging.getLogger("memovi.test.stamp")
        with caplog.at_level(logging.INFO, logger="memovi.test.stamp"):
            log_operation(logger, operation="stamp.op", status="success")
        assert len(caplog.records) == 1
        assert caplog.records[0].request_id == "req-stamp-1"
        assert caplog.records[0].workspace_id == WorkspaceId.default().value
    finally:
        clear_request_context(token)


def test_log_operation_sets_consistent_fields(caplog) -> None:
    logger = logging.getLogger("memovi.test.ops")
    with caplog.at_level(logging.INFO, logger="memovi.test.ops"):
        log_operation(
            logger,
            operation="repo.save",
            status="success",
            duration_ms=3.14,
            repository="SqlAlchemyDocumentRepository",
        )

    assert len(caplog.records) == 1
    record = caplog.records[0]
    assert record.operation == "repo.save"
    assert record.status == "success"
    assert record.duration_ms == 3.14
    assert record.repository == "SqlAlchemyDocumentRepository"
