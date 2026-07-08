from bolt_core.tool_operations import operation_for_tool


def test_operation_for_tool_covers_supported_write_terminal_and_web_tools():
    assert operation_for_tool("file.read") == "read"
    assert operation_for_tool("file.patch") == "patch"
    assert operation_for_tool("terminal.spawn") == "spawn"
    assert operation_for_tool("terminal.poll") == "poll"
    assert operation_for_tool("terminal.kill") == "kill"
    assert operation_for_tool("web.extract") == "extract"


def test_operation_for_tool_defaults_unknown_tools_to_read_only_shape():
    assert operation_for_tool("unknown.tool") == "read"
