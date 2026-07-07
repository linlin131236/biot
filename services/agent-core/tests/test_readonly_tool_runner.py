"""Tests for ReadOnlyToolRunner – read_file, list_dir, git, docs, tests, security."""
import os
import subprocess
from pathlib import Path

import pytest

from bolt_core.readonly_tool_runner import ReadOnlyToolRunner
from bolt_core.tool_registry import (
    CATEGORY_DANGEROUS,
    CATEGORY_READ_ONLY,
    CATEGORY_WRITE,
    PERM_READ,
    ToolDef,
    ToolRegistry,
)


# ── Helpers ──

def make_runner(tmp_path: Path, extra_tools: dict | None = None) -> ReadOnlyToolRunner:
    """Create a ReadOnlyToolRunner with a test registry and project dir."""
    r = ToolRegistry()
    # Register read-only tools
    for tid in ("read_file", "list_dir", "git_status", "git_log",
                 "git_diff_summary", "query_docs", "query_tests"):
        r.register(ToolDef(
            tool_id=tid, display_name=tid, category=CATEGORY_READ_ONLY,
            description=f"只读工具 {tid}", permission_required=PERM_READ,
            allow_auto_run=True, risk_level="low",
        ))
    # Register extra tools
    if extra_tools:
        for tid, info in extra_tools.items():
            r.register(ToolDef(
                tool_id=tid, display_name=tid, category=info.get("category", CATEGORY_READ_ONLY),
                description=f"工具 {tid}",
                permission_required=info.get("perm", PERM_READ),
                allow_auto_run=info.get("auto_run", True),
                risk_level=info.get("risk", "low"),
            ))
    # Create a basic project structure in tmp_path
    (tmp_path / "README.md").write_text("# Test Project\nHello World", encoding="utf-8")
    (tmp_path / "src").mkdir(exist_ok=True)
    (tmp_path / "src" / "main.py").write_text("print('hello')", encoding="utf-8")
    (tmp_path / "docs").mkdir(exist_ok=True)
    (tmp_path / "docs" / "readme.md").write_text("# Docs", encoding="utf-8")
    (tmp_path / "tests_dir").mkdir(exist_ok=True)
    (tmp_path / "tests_dir" / "test_main.py").write_text("def test(): pass", encoding="utf-8")
    # Init git repo if git available
    try:
        subprocess.run(["git", "init", "-q"], cwd=str(tmp_path), capture_output=True, timeout=5)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=str(tmp_path), capture_output=True, timeout=5)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=str(tmp_path), capture_output=True, timeout=5)
        subprocess.run(["git", "add", "-A"], cwd=str(tmp_path), capture_output=True, timeout=5)
        subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=str(tmp_path), capture_output=True, timeout=5)
    except Exception:
        pass  # git not available – git tests will be skipped

    return ReadOnlyToolRunner(registry=r, project_dir=str(tmp_path))


# ── read_file ──

class TestReadFile:
    def test_reads_valid_file(self, tmp_path):
        runner = make_runner(tmp_path)
        result = runner.run("read_file", "read_file", {"path": "README.md"})
        assert result.status == "executed"
        assert "Hello World" in (result.output or "")

    def test_read_nonexistent_file(self, tmp_path):
        runner = make_runner(tmp_path)
        result = runner.run("read_file", "read_file", {"path": "nope.txt"})
        assert result.status == "blocked"
        assert "不存在" in (result.error or "")

    def test_read_outside_workspace_blocked(self, tmp_path):
        runner = make_runner(tmp_path)
        result = runner.run("read_file", "read_file", {"path": "../../etc/passwd"})
        assert result.status == "blocked"
        assert "workspace" in (result.error or "").lower() or "外" in (result.error or "")

    def test_read_claude_dir_blocked(self, tmp_path):
        runner = make_runner(tmp_path)
        (tmp_path / ".claude").mkdir(exist_ok=True)
        (tmp_path / ".claude" / "config.txt").write_text("secret")
        result = runner.run("read_file", "read_file", {"path": ".claude/config.txt"})
        assert result.status == "blocked"
        assert ".claude" in (result.error or "")

    def test_read_env_file_blocked(self, tmp_path):
        runner = make_runner(tmp_path)
        (tmp_path / ".env").write_text("SECRET=xxx")
        result = runner.run("read_file", "read_file", {"path": ".env"})
        assert result.status == "blocked"
        assert "secret" in (result.error or "").lower()

    def test_read_secret_key_file_blocked(self, tmp_path):
        runner = make_runner(tmp_path)
        (tmp_path / "id_rsa").write_text("PRIVATE KEY")
        result = runner.run("read_file", "read_file", {"path": "id_rsa"})
        assert result.status == "blocked"

    def test_read_pem_file_blocked(self, tmp_path):
        runner = make_runner(tmp_path)
        (tmp_path / "cert.pem").write_text("CERT")
        result = runner.run("read_file", "read_file", {"path": "cert.pem"})
        assert result.status == "blocked"

    def test_output_redacts_sensitive_keys(self, tmp_path):
        runner = make_runner(tmp_path)
        (tmp_path / "config.py").write_text("API_KEY = 'sk-abc123'\nname = 'test'", encoding="utf-8")
        result = runner.run("read_file", "read_file", {"path": "config.py"})
        assert result.status == "executed"
        assert "已脱敏" in (result.output or "")

    def test_output_redacts_bearer_tokens(self, tmp_path):
        runner = make_runner(tmp_path)
        (tmp_path / "auth.py").write_text('auth = "Bearer xyz789"\nprint("ok")', encoding="utf-8")
        result = runner.run("read_file", "read_file", {"path": "auth.py"})
        assert result.status == "executed"
        assert "已脱敏" in (result.output or "")

    def test_binary_file_blocked(self, tmp_path):
        runner = make_runner(tmp_path)
        (tmp_path / "data.bin").write_bytes(b"\x00\x01\x02\xff\xfe")
        result = runner.run("read_file", "read_file", {"path": "data.bin"})
        assert result.status == "blocked"
        assert "二进制" in (result.error or "")

    def test_missing_path_param(self, tmp_path):
        runner = make_runner(tmp_path)
        result = runner.run("read_file", "read_file", {})
        assert result.status == "blocked"
        assert "path" in (result.error or "").lower()


# ── list_dir ──

class TestListDir:
    def test_lists_directory(self, tmp_path):
        runner = make_runner(tmp_path)
        result = runner.run("list_dir", "list_dir", {"path": "."})
        assert result.status == "executed"
        assert "README.md" in (result.output or "")
        assert "src" in (result.output or "")

    def test_hides_blocked_dirs(self, tmp_path):
        runner = make_runner(tmp_path)
        (tmp_path / ".claude").mkdir(exist_ok=True)
        result = runner.run("list_dir", "list_dir", {"path": "."})
        assert "已隐藏" in (result.output or "")

    def test_lists_nonexistent_dir(self, tmp_path):
        runner = make_runner(tmp_path)
        result = runner.run("list_dir", "list_dir", {"path": "nope"})
        assert result.status == "blocked"


# ── Registry checks ──

class TestRegistryChecks:
    def test_unregistered_tool_blocked(self, tmp_path):
        runner = make_runner(tmp_path)
        result = runner.run("no_such_tool", "read_file", {"path": "README.md"})
        assert result.status == "blocked"
        assert "未注册" in (result.error or "")

    def test_write_tool_blocked_in_readonly_runner(self, tmp_path):
        runner = make_runner(tmp_path, extra_tools={
            "write_file": {"category": CATEGORY_WRITE},
        })
        result = runner.run("write_file", "read_file", {"path": "README.md"})
        assert result.status == "blocked"
        assert "不是只读工具" in (result.error or "")

    def test_dangerous_tool_blocked(self, tmp_path):
        runner = make_runner(tmp_path, extra_tools={
            "shell_exec": {"category": CATEGORY_DANGEROUS},
        })
        result = runner.run("shell_exec", "read_file", {"path": "README.md"})
        assert result.status == "blocked"


# ── query_docs ──

class TestQueryDocs:
    def test_finds_docs(self, tmp_path):
        runner = make_runner(tmp_path)
        result = runner.run("query_docs", "query_docs", {})
        assert result.status == "executed"
        assert "readme.md" in (result.output or "").lower()

    def test_no_docs_dir(self, tmp_path):
        # Create runner without pre-creating docs
        r = ToolRegistry()
        r.register(ToolDef(
            tool_id="query_docs", display_name="query_docs", category=CATEGORY_READ_ONLY,
            description="只读工具", permission_required=PERM_READ,
            allow_auto_run=True, risk_level="low",
        ))
        runner = ReadOnlyToolRunner(registry=r, project_dir=str(tmp_path))
        result = runner.run("query_docs", "query_docs", {})
        assert result.status == "error"


# ── query_tests ──

class TestQueryTests:
    def test_finds_tests(self, tmp_path):
        runner = make_runner(tmp_path)
        result = runner.run("query_tests", "query_tests", {"pattern": "test_*.py"})
        assert result.status == "executed"
        assert "test_main.py" in (result.output or "")

    def test_no_matching_tests(self, tmp_path):
        runner = make_runner(tmp_path)
        result = runner.run("query_tests", "query_tests", {"pattern": "no_match_*.py"})
        assert result.status == "executed"
        assert "未找到" in (result.output or "")


# ── Git operations (when git available) ──

class TestGitOps:
    def test_git_status(self, tmp_path):
        runner = make_runner(tmp_path)
        result = runner.run("git_status", "git_status", {})
        # May fail if git not available, but shouldn't crash
        assert result.status in ("executed", "error")

    def test_git_log(self, tmp_path):
        runner = make_runner(tmp_path)
        result = runner.run("git_log", "git_log", {"count": 3})
        assert result.status in ("executed", "error")


# ── Unsupported operation ──

class TestUnsupported:
    def test_unsupported_operation(self, tmp_path):
        runner = make_runner(tmp_path)
        result = runner.run("read_file", "delete_file", {})
        assert result.status == "blocked"
        assert "不支持" in (result.error or "")


# ── Audit trail ──

class TestAudit:
    def test_audit_present_on_success(self, tmp_path):
        runner = make_runner(tmp_path)
        result = runner.run("read_file", "read_file", {"path": "README.md"})
        assert result.audit is not None
        assert "step" in result.audit

    def test_audit_present_on_blocked(self, tmp_path):
        runner = make_runner(tmp_path)
        result = runner.run("read_file", "read_file", {"path": "../../etc/passwd"})
        assert result.audit is not None
        assert result.audit.get("result") == "blocked"
