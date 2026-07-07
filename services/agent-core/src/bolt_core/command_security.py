"""Command parsing for process execution without a shell."""

from __future__ import annotations

import shlex
import sys
from dataclasses import dataclass


@dataclass(frozen=True)
class ParsedCommand:
    argv: list[str]
    display: str


SHELL_CONTROL_CHARS = {";", "|", "&", "<", ">", "`"}


def parse_command_argv(command: str) -> tuple[ParsedCommand | None, str | None]:
    stripped = command.strip()
    if not stripped:
        return None, "empty command"
    blocked = _first_shell_control(stripped)
    if blocked is not None:
        return None, f"shell control syntax not allowed: {blocked}"
    try:
        argv = shlex.split(stripped, posix=True)
    except ValueError as exc:
        return None, f"invalid command syntax: {exc}"
    if not argv:
        return None, "empty command"
    if argv[0].lower() == "echo":
        argv = [
            sys.executable,
            "-c",
            "import sys; print(' '.join(sys.argv[1:]))",
            *argv[1:],
        ]
    return ParsedCommand(argv=argv, display=stripped), None


def _first_shell_control(command: str) -> str | None:
    quote: str | None = None
    escaped = False
    index = 0
    while index < len(command):
        char = command[index]
        if escaped:
            escaped = False
            index += 1
            continue
        if char == "\\":
            escaped = True
            index += 1
            continue
        if quote:
            if char == quote:
                quote = None
            index += 1
            continue
        if char in {"'", '"'}:
            quote = char
            index += 1
            continue
        if char == "$" and index + 1 < len(command) and command[index + 1] == "(":
            return "$("
        if char in SHELL_CONTROL_CHARS or char in {"\n", "\r"}:
            return char
        index += 1
    return None
