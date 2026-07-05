"""OpenAI function-calling tool schemas for Bolt supported operations.

Generated from permission_gate.SUPPORTED_OPERATIONS. This is the single source
of truth for what parameter shapes the LLM sees when making tool calls.
"""

from bolt_core.permission_gate import SUPPORTED_OPERATIONS

FILE_READ_SCHEMA = {
    "type": "function",
    "function": {
        "name": "file.read",
        "description": "Read a file from the workspace. Returns file content.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Absolute or workspace-relative file path",
                },
            },
            "required": ["path"],
        },
    },
}

FILES_SEARCH_SCHEMA = {
    "type": "function",
    "function": {
        "name": "files.search",
        "description": "Search workspace files by name or content.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query string",
                },
                "mode": {
                    "type": "string",
                    "description": "Search mode: 'name' or 'content'",
                    "enum": ["name", "content"],
                },
            },
            "required": ["query"],
        },
    },
}

FILE_WRITE_SCHEMA = {
    "type": "function",
    "function": {
        "name": "file.write",
        "description": "Write content to a file in the workspace. Requires user confirmation.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Absolute or workspace-relative file path",
                },
                "proposed_content": {
                    "type": "string",
                    "description": "The new content to write to the file",
                },
            },
            "required": ["path", "proposed_content"],
        },
    },
}

SHELL_EXECUTE_SCHEMA = {
    "type": "function",
    "function": {
        "name": "shell.execute",
        "description": "Execute a shell command in the workspace. Requires user confirmation for most commands.",
        "parameters": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The shell command to execute",
                },
                "workdir": {
                    "type": "string",
                    "description": "Working directory for the command",
                },
            },
            "required": ["command"],
        },
    },
}

_TOOL_SCHEMAS = {
    "file.read": FILE_READ_SCHEMA,
    "files.search": FILES_SEARCH_SCHEMA,
    "file.write": FILE_WRITE_SCHEMA,
    "shell.execute": SHELL_EXECUTE_SCHEMA,
}


def all_tool_schemas() -> list[dict]:
    """Return OpenAI function-calling tool definitions for all supported operations."""
    return list(_TOOL_SCHEMAS.values())


def tool_schema(name: str) -> dict | None:
    """Return the tool schema for a given tool name, or None."""
    return _TOOL_SCHEMAS.get(name)
