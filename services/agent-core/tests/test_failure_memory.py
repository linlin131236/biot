from bolt_core.failure_memory import FailureMemory, FailureStore, ToolFailure


def test_failure_memory_adds_do_not_repeat_constraint():
    store = FailureStore()
    failure = ToolFailure(
        tool="image_generation",
        operation="create_icon",
        failure_class="quality_mismatch",
        observable_result="icon unreadable at 16px",
        root_cause="no small-size verification",
        repair_result="not_verified",
    )

    memory = store.record(failure)

    assert isinstance(memory, FailureMemory)
    assert memory.status == "unresolved"
    assert "Do not retry create_icon without changing strategy" in memory.do_not_repeat


def test_p0_context_contains_unresolved_failure():
    store = FailureStore()
    store.record(
        ToolFailure(
            tool="shell",
            operation="pnpm test",
            failure_class="test_failure",
            observable_result="risk tests failed",
            root_cause="risk classifier missing",
            repair_result="not_fixed",
        )
    )

    context = store.p0_context()

    assert context["unresolved_failures"][0]["tool"] == "shell"
    assert context["hard_constraints"][0].startswith("Do not retry")
