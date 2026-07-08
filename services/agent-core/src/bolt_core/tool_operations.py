"""Shared tool name to operation mapping."""

TOOL_OPERATION_BY_NAME = {
    "file.read": "read",
    "files.search": "search",
    "file.write": "write",
    "file.patch": "patch",
    "shell.execute": "command",
    "terminal.spawn": "spawn",
    "terminal.poll": "poll",
    "terminal.kill": "kill",
    "web.search": "search",
    "web.extract": "extract",
}


def operation_for_tool(tool_name: str) -> str:
    return TOOL_OPERATION_BY_NAME.get(tool_name, "read")
