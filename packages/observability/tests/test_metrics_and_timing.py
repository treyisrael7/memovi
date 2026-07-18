import logging

import pytest

from memovi_observability import (
    InMemoryMetricsRecorder,
    set_metrics_recorder,
    timed_operation,
)


def test_in_memory_metrics_recorder_captures_counters_and_timings() -> None:
    recorder = InMemoryMetricsRecorder()
    recorder.increment("uploads", tags={"status": "ok"})
    recorder.timing("search.latency", 42.0, tags={"mode": "hybrid"})

    assert recorder.counters["uploads"] == 1.0
    assert recorder.timings["search.latency"] == [42.0]
    assert recorder.tagged_timings[0][2]["mode"] == "hybrid"


def test_timed_operation_records_success(caplog) -> None:
    recorder = InMemoryMetricsRecorder()
    set_metrics_recorder(recorder)

    with caplog.at_level(logging.INFO, logger="memovi.timing"):
        with timed_operation("repo.get", repository="SqlAlchemySearchRepository"):
            pass

    assert any(name.endswith(".count") for name in recorder.counters)
    assert any("repo.get" in name for name in recorder.timings)
    assert any(
        getattr(record, "operation", None) == "repo.get"
        and getattr(record, "status", None) == "success"
        and getattr(record, "repository", None) == "SqlAlchemySearchRepository"
        for record in caplog.records
    )


def test_timed_operation_records_error() -> None:
    recorder = InMemoryMetricsRecorder()
    set_metrics_recorder(recorder)

    with pytest.raises(RuntimeError, match="boom"):
        with timed_operation("repo.fail", repository="SqlAlchemySearchRepository"):
            raise RuntimeError("boom")

    assert any(
        name.endswith(".count") and tags.get("status") == "error"
        for name, _value, tags in recorder.tagged_counters
    )
