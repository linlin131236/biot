from bolt_core.trace import TraceLog


def test_trace_log_records_ordered_events():
    trace = TraceLog(run_id="run_1")

    first = trace.record("run.created", {"goal": "test"})
    second = trace.record("tool.requested", {"tool": "shell.run"})

    assert first.sequence == 1
    assert second.sequence == 2
    assert trace.events()[1].type == "tool.requested"


def test_trace_log_has_internal_lock_for_concurrent_recording():
    trace = TraceLog(run_id="run_1")

    assert hasattr(trace, "_lock")
