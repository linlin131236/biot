"""Read-only Tool Runner. Safely executes read-only tools with path validation,
secret blocking, output redaction, and audit trail. Never executes write/dangerous tools."""
from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from bolt_core.tool_registry import CATEGORY_READ_ONLY, ToolRegistry
from bolt_core.path_guard import PathGuard, PathCheck

# ── Blocked paths beyond what PathGuard covers ──
_BLOCKED_DIRS = {".claude", ".bolt", "__pycache__", ".git", "node_modules", "venv", ".venv"}
_BLOCKED_NAMES = {"uv.lock", "package-lock.json", "yarn.lock", "pnpm-lock.yaml"}

# ── Sensitive patterns for redaction ──
_SENSITIVE_KEY_PATTERNS = [
    "api_key", "apikey", "secret", "password", "token", "credential",
    "private_key", "privatekey", "access_key", "accesskey",
]
_SENSITIVE_VALUE_PATTERNS = [
    "Bearer ", "sk-", "pk-", "ghp_", "gho_", "github_pat_",
    "AKIA", "eyJ",  # AWS key prefix, JWT prefix
]


@dataclass(frozen=True)
class ReadOnlyToolResult:
    """Result of a read-only tool execution."""
    tool_id: str
    operation: str
    status: str  # executed / blocked / error
    output: str | None = None
    error: str | None = None
    audit: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "tool_id": self.tool_id,
            "operation": self.operation,
            "status": self.status,
            "output": self.output,
            "error": self.error,
            "audit": self.audit,
        }


class ReadOnlyToolRunner:
    """安全只读工具运行器。

    仅执行注册表中 category=read_only 的工具。所有操作受限于项目目录内。
    自动阻断敏感文件和目录，输出经过脱敏处理。
    """

    def __init__(self, registry: ToolRegistry, project_dir: str) -> None:
        self._registry = registry
        self._project_dir = Path(project_dir).resolve()
        self._path_guard = PathGuard(project_dir)

    # ── Public API ──

    def run(self, tool_id: str, operation: str, params: dict | None = None) -> ReadOnlyToolResult:
        """执行只读工具操作。仅限已注册的 read_only 工具。"""
        params = params or {}

        # ── 1. Registry check ──
        tool_def = self._registry.get(tool_id)
        if tool_def is None:
            return ReadOnlyToolResult(
                tool_id=tool_id, operation=operation, status="blocked",
                error=f"工具 '{tool_id}' 未注册。",
                audit={"step": "registry_check", "result": "blocked", "reason": "未注册"},
            )
        if tool_def.category != CATEGORY_READ_ONLY:
            return ReadOnlyToolResult(
                tool_id=tool_id, operation=operation, status="blocked",
                error=f"工具 '{tool_id}' 类别为 '{tool_def.category}'，不是只读工具。只读运行器仅执行只读工具。",
                audit={"step": "registry_check", "result": "blocked",
                       "reason": f"类别不匹配: {tool_def.category}"},
            )

        # ── 2. Dispatch ──
        try:
            if operation == "read_file":
                return self._read_file(params)
            elif operation == "list_dir":
                return self._list_dir(params)
            elif operation == "git_status":
                return self._git_status()
            elif operation == "git_log":
                return self._git_log(params)
            elif operation == "git_diff_summary":
                return self._git_diff_summary()
            elif operation == "query_docs":
                return self._query_docs()
            elif operation == "query_tests":
                return self._query_tests(params)
            else:
                return ReadOnlyToolResult(
                    tool_id=tool_id, operation=operation, status="blocked",
                    error=f"不支持的操作: '{operation}'。支持: read_file, list_dir, git_status, git_log, git_diff_summary, query_docs, query_tests",
                    audit={"step": "dispatch", "result": "blocked", "reason": f"不支持的操作: {operation}"},
                )
        except Exception as e:
            return ReadOnlyToolResult(
                tool_id=tool_id, operation=operation, status="error",
                error=f"执行异常: {e}",
                audit={"step": "execute", "result": "error", "reason": str(e)},
            )

    # ── Operations ──

    def _read_file(self, params: dict) -> ReadOnlyToolResult:
        path = str(params.get("path", "")).strip()
        if not path:
            return self._blocked("read_file", "缺少 path 参数")

        # Path validation
        check = self._check_path(path)
        if not check.allowed:
            return self._blocked("read_file", check.reason)

        # Read
        try:
            data = check.path.read_bytes()
            if len(data) > 256 * 1024:
                return self._blocked("read_file", f"文件过大: {len(data)} 字节，超过 256KB 限制")
            try:
                text = data.decode("utf-8")
            except UnicodeDecodeError:
                return self._blocked("read_file", "二进制文件不可读")
        except FileNotFoundError:
            return self._blocked("read_file", f"文件不存在: {check.path}")
        except OSError as e:
            return self._error("read_file", f"读取错误: {e}")

        # Redact
        safe_text = self._redact(text)

        return ReadOnlyToolResult(
            tool_id="read_file", operation="read_file", status="executed",
            output=safe_text,
            audit={"step": "read_file", "result": "executed", "path": str(check.path),
                   "size_bytes": len(data)},
        )

    def _list_dir(self, params: dict) -> ReadOnlyToolResult:
        path = str(params.get("path", ".")).strip()
        check = self._check_path(path)
        if not check.allowed:
            return self._blocked("list_dir", check.reason)

        if not check.path.is_dir():
            return self._blocked("list_dir", f"不是目录: {check.path}")

        try:
            entries = []
            for p in sorted(check.path.iterdir()):
                name = p.name
                if name in _BLOCKED_DIRS or name in _BLOCKED_NAMES:
                    entries.append(f"[已隐藏] {name}")
                elif p.is_dir():
                    entries.append(f"[目录] {name}/")
                else:
                    size = p.stat().st_size if p.is_file() else 0
                    entries.append(f"[文件] {name} ({self._format_size(size)})")
            output = "\n".join(entries) if entries else "(空目录)"
        except OSError as e:
            return self._error("list_dir", f"列出目录错误: {e}")

        return ReadOnlyToolResult(
            tool_id="list_dir", operation="list_dir", status="executed",
            output=output,
            audit={"step": "list_dir", "result": "executed", "path": str(check.path),
                   "entry_count": len(entries)},
        )

    def _git_status(self) -> ReadOnlyToolResult:
        return self._run_git(["status", "--short", "--branch"])

    def _git_log(self, params: dict) -> ReadOnlyToolResult:
        count = min(int(params.get("count", 10)), 50)
        return self._run_git(["log", f"--oneline", f"-{count}", "--decorate"])

    def _git_diff_summary(self) -> ReadOnlyToolResult:
        return self._run_git(["diff", "--stat"])

    def _query_docs(self) -> ReadOnlyToolResult:
        docs_dir = self._project_dir / "docs"
        if not docs_dir.is_dir():
            return self._error("query_docs", "docs 目录不存在")

        try:
            md_files = sorted(docs_dir.rglob("*.md"))
            # Filter blocked dirs
            visible = [f for f in md_files if not any(b in str(f) for b in _BLOCKED_DIRS)]
            if not visible:
                output = "(docs 目录下无可见 .md 文件)"
            else:
                output = "\n".join(str(f.relative_to(self._project_dir)) for f in visible[:100])
                if len(visible) > 100:
                    output += f"\n... 还有 {len(visible) - 100} 个文件"
        except OSError as e:
            return self._error("query_docs", f"查询 docs 错误: {e}")

        return ReadOnlyToolResult(
            tool_id="query_docs", operation="query_docs", status="executed",
            output=output,
            audit={"step": "query_docs", "result": "executed", "file_count": len(visible)},
        )

    def _query_tests(self, params: dict) -> ReadOnlyToolResult:
        pattern = str(params.get("pattern", "test_*.py"))
        try:
            test_files = sorted(self._project_dir.rglob(pattern))
            visible = [f for f in test_files if not any(b in str(f) for b in _BLOCKED_DIRS)]
            if not visible:
                output = f"(未找到匹配 '{pattern}' 的测试文件)"
            else:
                output = "\n".join(str(f.relative_to(self._project_dir)) for f in visible[:100])
                if len(visible) > 100:
                    output += f"\n... 还有 {len(visible) - 100} 个文件"
        except OSError as e:
            return self._error("query_tests", f"查询测试错误: {e}")

        return ReadOnlyToolResult(
            tool_id="query_tests", operation="query_tests", status="executed",
            output=output,
            audit={"step": "query_tests", "result": "executed", "file_count": len(visible)},
        )

    # ── Helpers ──

    def _check_path(self, target: str) -> PathCheck:
        """Validate a path with extended blocking rules."""
        # Base PathGuard check
        check = self._path_guard.check(target)
        if not check.allowed:
            return check

        # Extra: block .claude/ and other forbidden dirs
        resolved = check.path
        parts = [p.lower() for p in resolved.parts]
        for blocked in _BLOCKED_DIRS:
            if blocked in parts:
                return PathCheck(False, resolved, f"禁止访问目录: {blocked}/")

        if resolved.name in _BLOCKED_NAMES:
            return PathCheck(False, resolved, f"禁止访问文件: {resolved.name}")

        return check

    def _run_git(self, args: list[str]) -> ReadOnlyToolResult:
        """Run a read-only git command."""
        cmd = ["git"] + args
        try:
            result = subprocess.run(
                cmd, cwd=str(self._project_dir), capture_output=True,
                text=True, timeout=15,
            )
            output = result.stdout.strip() or "(无输出)"
            if result.returncode != 0:
                err = result.stderr.strip()
                return self._error("git", f"git {' '.join(args)} 失败: {err}")
        except subprocess.TimeoutExpired:
            return self._error("git", "git 命令超时 (15s)")
        except FileNotFoundError:
            return self._error("git", "git 命令不可用")
        except Exception as e:
            return self._error("git", f"git 异常: {e}")

        return ReadOnlyToolResult(
            tool_id="git", operation="git", status="executed",
            output=output,
            audit={"step": "git", "result": "executed", "command": " ".join(cmd)},
        )

    def _redact(self, text: str) -> str:
        """Redact sensitive content from output text."""
        lines = text.split("\n")
        redacted = []
        for line in lines:
            lower = line.lower()
            if any(pattern in lower for pattern in _SENSITIVE_KEY_PATTERNS):
                redacted.append("[已脱敏] 包含敏感键名的行")
                continue
            if any(pattern in line for pattern in _SENSITIVE_VALUE_PATTERNS):
                redacted.append("[已脱敏] 包含疑似凭证/token 的行")
                continue
            redacted.append(line)
        return "\n".join(redacted)

    @staticmethod
    def _format_size(size_bytes: int) -> str:
        if size_bytes < 1024:
            return f"{size_bytes}B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f}KB"
        else:
            return f"{size_bytes / (1024 * 1024):.1f}MB"

    @staticmethod
    def _blocked(operation: str, reason: str) -> ReadOnlyToolResult:
        return ReadOnlyToolResult(
            tool_id=operation, operation=operation, status="blocked",
            error=reason,
            audit={"step": operation, "result": "blocked", "reason": reason},
        )

    @staticmethod
    def _error(operation: str, reason: str) -> ReadOnlyToolResult:
        return ReadOnlyToolResult(
            tool_id=operation, operation=operation, status="error",
            error=reason,
            audit={"step": operation, "result": "error", "reason": reason},
        )
