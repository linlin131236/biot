"""Safe Test Runner Integration. Only runs whitelisted test commands with budget control.

Never allows arbitrary shell commands. Results are structured and redacted.
"""
from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# ── Whitelisted test commands ──
_TEST_COMMAND_WHITELIST: dict[str, dict] = {
    "backend_unit": {
        "command": ["uv", "run", "pytest", "-q", "--color=no", "-k", "not _api"],
        "description": "后端单元测试（不含 API 测试）",
        "cwd_subdir": "services/agent-core",
        "timeout_seconds": 180,
        "max_output_bytes": 50 * 1024,
    },
    "backend_api": {
        "command": ["uv", "run", "pytest", "-q", "--color=no", "-k", "_api"],
        "description": "后端 API 测试",
        "cwd_subdir": "services/agent-core",
        "timeout_seconds": 300,
        "max_output_bytes": 50 * 1024,
    },
    "backend_targeted": {
        "command": ["uv", "run", "pytest", "-q", "--color=no"],
        "description": "后端全量测试",
        "cwd_subdir": "services/agent-core",
        "timeout_seconds": 600,
        "max_output_bytes": 100 * 1024,
    },
    "shared_test": {
        "command": ["pnpm", "--filter", "@bolt/shared", "test"],
        "description": "共享模块测试",
        "cwd_subdir": ".",
        "timeout_seconds": 60,
        "max_output_bytes": 20 * 1024,
    },
    "desktop_test": {
        "command": ["pnpm", "--filter", "@bolt/desktop", "test"],
        "description": "桌面端测试",
        "cwd_subdir": ".",
        "timeout_seconds": 120,
        "max_output_bytes": 30 * 1024,
    },
    "desktop_build": {
        "command": ["pnpm", "--filter", "@bolt/desktop", "build"],
        "description": "桌面端构建",
        "cwd_subdir": ".",
        "timeout_seconds": 60,
        "max_output_bytes": 20 * 1024,
    },
    "quality_gate": {
        "command": ["pnpm", "run", "quality"],
        "description": "全量质量门禁",
        "cwd_subdir": ".",
        "timeout_seconds": 600,
        "max_output_bytes": 100 * 1024,
    },
}

# ── Dangerous command patterns (always blocked) ──
_DANGEROUS_PATTERNS = [
    "push", "release", "tag", "delete", "rm -rf", "format",
    "> /dev", "| sh", "$(", "`", ";", "&& rm", "&& sudo",
]


@dataclass(frozen=True)
class TestRunResult:
    """Structured result of a test run."""
    test_id: str
    status: str  # passed / failed / timed_out / blocked / error
    exit_code: int | None = None
    summary: str = ""
    output_snippet: str = ""
    evidence_hash: str = ""

    def to_dict(self) -> dict:
        return {
            "test_id": self.test_id,
            "status": self.status,
            "exit_code": self.exit_code,
            "summary": self.summary,
            "output_snippet": self.output_snippet,
            "evidence_hash": self.evidence_hash,
        }


class TestRunnerIntegration:
    """安全测试运行集成。只允许白名单命令，不允许任意 shell 命令。"""

    def __init__(self, project_dir: str = ".") -> None:
        self._project_dir = Path(project_dir).resolve()
        self._history: list[TestRunResult] = []

    def run(self, test_id: str, extra_args: list[str] | None = None) -> TestRunResult:
        """运行白名单测试命令。返回结构化结果。不自动修复。"""
        # ── Check whitelist ──
        config = _TEST_COMMAND_WHITELIST.get(test_id)
        if config is None:
            result_obj = TestRunResult(
                test_id=test_id, status="blocked",
                summary=f"测试 '{test_id}' 不在白名单中。可用: {list(_TEST_COMMAND_WHITELIST)}",
            )
            self._history.append(result_obj)
            return result_obj

        # ── Build command ──
        cmd = list(config["command"])
        if extra_args:
            for arg in extra_args:
                arg_str = str(arg)
                # Block dangerous patterns in extra args
                if any(p in arg_str for p in _DANGEROUS_PATTERNS):
                    result_obj = TestRunResult(
                        test_id=test_id, status="blocked",
                        summary=f"参数 '{arg_str}' 包含危险模式，已阻止。",
                    )
                    self._history.append(result_obj)
                    return result_obj
                cmd.append(arg_str)

        # ── Determine cwd ──
        cwd = self._project_dir / config["cwd_subdir"]
        if not cwd.is_dir():
            result_obj = TestRunResult(
                test_id=test_id, status="error",
                summary=f"工作目录不存在: {cwd}",
            )
            self._history.append(result_obj)
            return result_obj

        # ── Security: ensure cwd is within project ──
        try:
            cwd.resolve().relative_to(self._project_dir)
        except ValueError:
            result_obj = TestRunResult(
                test_id=test_id, status="blocked",
                summary=f"工作目录 '{cwd}' 超出项目目录范围",
            )
            self._history.append(result_obj)
            return result_obj

        # ── Execute ──
        timeout = config["timeout_seconds"]
        max_bytes = config["max_output_bytes"]

        try:
            result = subprocess.run(
                cmd, cwd=str(cwd), capture_output=True,
                text=True, timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            result_obj = TestRunResult(
                test_id=test_id, status="timed_out",
                exit_code=None,
                summary=f"测试超时（{timeout}s）",
                output_snippet="",
            )
            self._history.append(result_obj)
            return result_obj
        except FileNotFoundError:
            result_obj = TestRunResult(
                test_id=test_id, status="error",
                summary=f"命令不可用: {cmd[0]}",
            )
            self._history.append(result_obj)
            return result_obj
        except Exception as e:
            result_obj = TestRunResult(
                test_id=test_id, status="error",
                summary=f"执行异常: {e}",
            )
            self._history.append(result_obj)
            return result_obj

        # ── Process output ──
        output = (result.stdout + "\n" + result.stderr).strip()
        snippet = output[-max_bytes:] if len(output) > max_bytes else output
        if len(output) > max_bytes:
            snippet = f"... (输出截断，原始 {len(output)} 字节)\n{snippet}"

        # ── Redact sensitive content ──
        snippet = self._redact(snippet)

        # ── Classify result ──
        import hashlib
        evidence_hash = hashlib.sha256(output.encode()).hexdigest()[:16]

        if result.returncode == 0:
            status = "passed"
            # Extract summary from pytest output
            summary = self._extract_summary(output)
        else:
            status = "failed"
            summary = f"测试失败 (exit code: {result.returncode})"

        result_obj = TestRunResult(
            test_id=test_id, status=status,
            exit_code=result.returncode,
            summary=summary,
            output_snippet=snippet,
            evidence_hash=evidence_hash,
        )
        self._history.append(result_obj)
        return result_obj

    def history(self) -> list[dict]:
        """返回测试运行历史。只读。"""
        return [r.to_dict() for r in self._history]

    def list_available(self) -> dict:
        """列出所有白名单测试命令。"""
        return {
            "available_tests": {
                tid: {"description": cfg["description"], "timeout_seconds": cfg["timeout_seconds"]}
                for tid, cfg in _TEST_COMMAND_WHITELIST.items()
            },
            "disclaimer": "仅白名单测试命令可运行。不允许任意 shell 命令。不自动修复测试失败。",
        }

    # ── Internal ──

    @staticmethod
    def _redact(text: str) -> str:
        """Basic output redaction."""
        patterns = ["api_key", "apikey", "secret", "password", "token", "credential"]
        lines = text.split("\n")
        result = []
        for line in lines:
            lower = line.lower()
            if any(p in lower for p in patterns):
                result.append("[已脱敏]")
            else:
                result.append(line)
        return "\n".join(result)

    @staticmethod
    def _extract_summary(output: str) -> str:
        """Extract the pytest summary line."""
        for line in output.split("\n"):
            if "passed" in line and ("failed" in line or "error" in line or "warning" in line):
                return line.strip()
        # Return last meaningful line
        lines = [l.strip() for l in output.split("\n") if l.strip()]
        if lines:
            return lines[-1]
        return "测试完成"
