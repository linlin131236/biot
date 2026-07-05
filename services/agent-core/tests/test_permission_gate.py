from bolt_core.permission_gate import PermissionGate
from bolt_core.tool_protocol import ToolRequest


def test_write_request_requires_permission_with_diff():
    gate = PermissionGate(workspace="D:/Bolt/Bolt")
    request = ToolRequest.create(
        tool="file.write",
        operation="write",
        payload={"path": "D:/Bolt/Bolt/src/app.ts"},
    )

    decision = gate.evaluate(request)

    assert decision.action == "confirm_with_diff"
    assert decision.status == "pending_permission"


def test_file_read_inside_workspace_is_allowed():
    gate = PermissionGate(workspace="D:/Bolt/Bolt")
    request = ToolRequest.create(
        tool="file.read",
        operation="read",
        payload={"path": "D:/Bolt/Bolt/src/app.ts"},
    )

    decision = gate.evaluate(request)

    assert decision.action == "allow"
    assert decision.status == "allowed"


def test_files_search_is_allowed():
    gate = PermissionGate(workspace="D:/Bolt/Bolt")
    request = ToolRequest.create(
        tool="files.search",
        operation="search",
        payload={"query": "app"},
    )

    decision = gate.evaluate(request)

    assert decision.action == "allow"
    assert decision.status == "allowed"


def test_file_read_secret_path_is_denied():
    gate = PermissionGate(workspace="D:/Bolt/Bolt")
    request = ToolRequest.create(
        tool="file.read",
        operation="read",
        payload={"path": "D:/Bolt/Bolt/.env"},
    )

    decision = gate.evaluate(request)

    assert decision.action == "deny"
    assert decision.status == "denied"


def test_shell_execute_requires_confirmation():
    gate = PermissionGate(workspace="D:/Bolt/Bolt")
    request = ToolRequest.create(
        tool="shell.execute",
        operation="command",
        payload={"command": "pnpm test", "workdir": "D:/Bolt/Bolt"},
    )

    decision = gate.evaluate(request)

    assert decision.action == "confirm"
    assert decision.status == "pending_permission"


def test_dangerous_command_is_denied():
    gate = PermissionGate(workspace="D:/Bolt/Bolt")
    request = ToolRequest.create(
        tool="shell.run",
        operation="command",
        payload={"command": "rm -rf /"},
    )

    decision = gate.evaluate(request)

    assert decision.action == "deny"
    assert decision.status == "denied"
