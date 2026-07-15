"""Strict translation from audited ACP session updates to Bolt events."""

from __future__ import annotations

import re
from typing import Any

from bolt_core.runtime.events import RuntimeEventKind

_ID = re.compile(r"^[a-z][a-z0-9_-]{2,127}$")


def map_acp_update(update: object) -> tuple[RuntimeEventKind, dict[str, Any]]:
    if not isinstance(update, dict):
        raise ValueError("unsupported ACP update")
    kind = update.get("sessionUpdate")
    if kind == "agent_message_chunk":
        return RuntimeEventKind.MESSAGE_DELTA, {"text": _text_content(update)}
    if kind == "agent_thought_chunk":
        return RuntimeEventKind.THOUGHT, {"text": _text_content(update)}
    if kind == "plan":
        return RuntimeEventKind.PLAN_UPDATE, {"entries": _plan_entries(update)}
    if kind == "usage_update":
        return RuntimeEventKind.USAGE_UPDATE, _context_usage_payload(update)
    if kind == "tool_call":
        return RuntimeEventKind.TOOL_STARTED, _tool_payload(update)
    if kind == "tool_call_update":
        return _tool_update(update)
    raise ValueError("unsupported ACP session update")


def prompt_usage_payload(response: object) -> dict[str, int] | None:
    if not isinstance(response, dict) or "usage" not in response:
        return None
    usage = response["usage"]
    if not isinstance(usage, dict):
        raise ValueError("unsupported ACP prompt usage")
    return _usage_payload(usage)


def _text_content(update: dict[str, Any]) -> str:
    content = update.get("content")
    if not isinstance(content, dict) or content.get("type") != "text":
        raise ValueError("unsupported ACP text update")
    text = content.get("text")
    if not isinstance(text, str):
        raise ValueError("unsupported ACP text update")
    return text


def _plan_entries(update: dict[str, Any]) -> list[dict[str, Any]]:
    entries = update.get("entries")
    if not isinstance(entries, list) or any(not isinstance(entry, dict) for entry in entries):
        raise ValueError("unsupported ACP plan update")
    return entries


def _tool_payload(update: dict[str, Any]) -> dict[str, Any]:
    tool_id = update.get("toolCallId")
    if not isinstance(tool_id, str) or not _ID.fullmatch(tool_id):
        raise ValueError("unsupported ACP tool update")
    title = update.get("title")
    if not isinstance(title, str) or not title:
        raise ValueError("unsupported ACP tool update")
    result: dict[str, Any] = {"tool_id": tool_id, "title": title}
    if "kind" in update:
        result["tool_kind"] = update["kind"]
    return result


def _tool_update(update: dict[str, Any]) -> tuple[RuntimeEventKind, dict[str, Any]]:
    payload = _tool_payload(update)
    status = update.get("status")
    if status == "completed":
        return RuntimeEventKind.TOOL_COMPLETED, payload
    if status == "failed":
        return RuntimeEventKind.TOOL_FAILED, payload
    if status in {"pending", "in_progress"}:
        return RuntimeEventKind.TOOL_PROGRESS, payload
    raise ValueError("unsupported ACP tool status")


def _context_usage_payload(value: dict[str, Any]) -> dict[str, int]:
    size = value.get("size")
    used = value.get("used")
    if type(size) is not int or size < 0 or type(used) is not int or used < 0:
        raise ValueError("unsupported ACP context usage")
    return {"context_window": size, "context_used": used}


def _usage_payload(value: dict[str, Any]) -> dict[str, int]:
    names = {
        "inputTokens": "input_tokens",
        "outputTokens": "output_tokens",
        "totalTokens": "total_tokens",
        "thoughtTokens": "thought_tokens",
        "cachedReadTokens": "cached_read_tokens",
        "cachedWriteTokens": "cached_write_tokens",
    }
    result: dict[str, int] = {}
    for source, target in names.items():
        raw = value.get(source)
        if raw is None:
            continue
        if type(raw) is not int or raw < 0:
            raise ValueError("unsupported ACP usage value")
        result[target] = raw
    if not {"input_tokens", "output_tokens"} <= result.keys():
        raise ValueError("unsupported ACP usage value")
    return result
