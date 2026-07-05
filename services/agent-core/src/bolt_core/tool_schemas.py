"""OpenAI function-calling tool schemas for Bolt supported operations.

Generated from permission_gate.SUPPORTED_OPERATIONS. This is the single source
of truth for what parameter shapes the LLM sees when making tool calls.
"""

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

FILE_PATCH_SCHEMA = {
    "type": "function",
    "function": {
        "name": "file.patch",
        "description": "Apply a targeted find-and-replace edit to a file. Prefer this over file.write for small changes.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "File path in workspace",
                },
                "old_string": {
                    "type": "string",
                    "description": "Exact text to find (must be unique in file)",
                },
                "new_string": {
                    "type": "string",
                    "description": "Replacement text",
                },
            },
            "required": ["path", "old_string", "new_string"],
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

TERMINAL_SPAWN_SCHEMA = {
    "type": "function",
    "function": {
        "name": "terminal.spawn",
        "description": "Start a long-running command in the background. Returns a session_id.",
        "parameters": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The command to run in background",
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

TERMINAL_POLL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "terminal.poll",
        "description": "Check the output and status of a background process.",
        "parameters": {
            "type": "object",
            "properties": {
                "session_id": {
                    "type": "string",
                    "description": "The session_id returned by terminal.spawn",
                },
            },
            "required": ["session_id"],
        },
    },
}

TERMINAL_KILL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "terminal.kill",
        "description": "Kill a running background process.",
        "parameters": {
            "type": "object",
            "properties": {
                "session_id": {
                    "type": "string",
                    "description": "The session_id of the process to kill",
                },
            },
            "required": ["session_id"],
        },
    },
}

WEB_SEARCH_SCHEMA = {
    "type": "function",
    "function": {
        "name": "web.search",
        "description": "Search the web for information. Returns titles, URLs, and descriptions.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max results (default 5)",
                },
            },
            "required": ["query"],
        },
    },
}

WEB_EXTRACT_SCHEMA = {
    "type": "function",
    "function": {
        "name": "web.extract",
        "description": "Extract text content from web page URLs. Returns markdown.",
        "parameters": {
            "type": "object",
            "properties": {
                "urls": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "URLs to extract (max 5)",
                },
                "char_limit": {
                    "type": "integer",
                    "description": "Max characters per page (default 15000)",
                },
            },
            "required": ["urls"],
        },
    },
}

_TOOL_SCHEMAS = {
    "file.read": FILE_READ_SCHEMA,
    "files.search": FILES_SEARCH_SCHEMA,
    "file.write": FILE_WRITE_SCHEMA,
    "file.patch": FILE_PATCH_SCHEMA,
    "shell.execute": SHELL_EXECUTE_SCHEMA,
    "terminal.spawn": TERMINAL_SPAWN_SCHEMA,
    "terminal.poll": TERMINAL_POLL_SCHEMA,
    "terminal.kill": TERMINAL_KILL_SCHEMA,
    "web.search": WEB_SEARCH_SCHEMA,
    "web.extract": WEB_EXTRACT_SCHEMA,
}


def all_tool_schemas() -> list[dict]:
    """Return OpenAI function-calling tool definitions for all supported operations."""
    return list(_TOOL_SCHEMAS.values())


def tool_schema(name: str) -> dict | None:
    """Return the tool schema for a given tool name, or None."""
    return _TOOL_SCHEMAS.get(name)
