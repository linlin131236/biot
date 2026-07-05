from bolt_core.tool_protocol import ToolRequest, ToolResult


def test_tool_request_has_stable_id_and_payload():
    request = ToolRequest.create(
        tool="file.write",
        operation="write",
        payload={"path": "src/app.ts"},
    )

    assert request.id.startswith("tool_")
    assert request.tool == "file.write"
    assert request.payload["path"] == "src/app.ts"


def test_tool_result_records_denied_status():
    result = ToolResult.denied("tool_1", reason="destructive command denied")

    assert result.request_id == "tool_1"
    assert result.status == "denied"


def test_tool_result_records_execution_output():
    result = ToolResult.executed("tool_1", output="done")

    assert result.status == "executed"
    assert result.output == "done"
    assert result.error is None


def test_tool_result_records_execution_error():
    result = ToolResult.failed("tool_1", error="boom")

    assert result.status == "failed"
    assert result.output is None
    assert result.error == "boom"
