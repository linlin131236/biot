"""Unit tests for ToolSelectionPolicy. Classification only, no execution."""
import pytest

from bolt_core.tool_selection_policy import READ_ONLY, SIDE_EFFECT, DANGEROUS, UNKNOWN, ToolSelectionPolicy


def test_classify_read_only_tool():
    """Read-only tools are classified correctly."""
    result = ToolSelectionPolicy.classify("read_file")
    assert result["class"] == READ_ONLY
    assert result["label"] == "只读工具"


def test_classify_side_effect_tool():
    """Side-effect tools are classified correctly."""
    result = ToolSelectionPolicy.classify("write_file")
    assert result["class"] == SIDE_EFFECT
    assert result["label"] == "有副作用工具"


def test_classify_dangerous_tool():
    """Dangerous tools are classified correctly."""
    result = ToolSelectionPolicy.classify("git_push")
    assert result["class"] == DANGEROUS
    assert result["label"] == "危险工具"


def test_classify_unknown_tool():
    """Unknown tools return UNKNOWN class."""
    result = ToolSelectionPolicy.classify("nonexistent_tool")
    assert result["class"] == UNKNOWN
    assert result["label"] == "未知工具"


def test_list_tools_returns_all():
    """list_tools without filter returns all registered tools."""
    tools = ToolSelectionPolicy.list_tools()
    assert len(tools) > 10
    names = {t["name"] for t in tools}
    assert "read_file" in names
    assert "git_push" in names


def test_list_tools_filtered_by_class():
    """list_tools with class filter returns only that class."""
    dangerous = ToolSelectionPolicy.list_tools(DANGEROUS)
    assert all(t["class"] == DANGEROUS for t in dangerous)
    assert len(dangerous) >= 5  # git_push, git_delete, rm_file, rm_dir, shell_exec, release, tag, delete, permission_approve


def test_summary_returns_counts():
    """summary returns class counts."""
    s = ToolSelectionPolicy.summary()
    assert "classes" in s
    assert "counts" in s
    assert "total" in s
    assert s["counts"].get(DANGEROUS, 0) > 0


def test_select_read_only_no_permission():
    """Selecting read-only tools does not require permission."""
    result = ToolSelectionPolicy.select(["read_file", "git_status"], "查看代码")
    assert result["all_allowed"] is True
    assert result["any_requires_permission"] is False


def test_select_dangerous_requires_permission():
    """Selecting dangerous tools requires permission."""
    result = ToolSelectionPolicy.select(["git_push"], "发布代码")
    assert result["any_requires_permission"] is True
    assert result["results"][0]["requires_permission"] is True
    assert len(result["results"][0]["warnings"]) > 0


def test_select_side_effect_requires_permission():
    """Selecting side-effect tools requires permission."""
    result = ToolSelectionPolicy.select(["write_file", "git_commit"], "修改代码")
    assert result["any_requires_permission"] is True
    assert all(r["requires_permission"] for r in result["results"])


def test_select_unknown_tool_not_allowed():
    """Unknown tools are not allowed."""
    result = ToolSelectionPolicy.select(["nonexistent"], "测试")
    assert result["all_allowed"] is False
    assert result["results"][0]["allowed"] is False


def test_select_mixed_tools():
    """Mixed selection returns per-tool results."""
    result = ToolSelectionPolicy.select(["read_file", "git_push", "nonexistent"], "混合")
    assert result["all_allowed"] is False  # unknown tool
    assert result["any_requires_permission"] is True  # git_push
    assert len(result["results"]) == 3


def test_no_auto_execution():
    """ToolSelectionPolicy has no execution methods."""
    svc = ToolSelectionPolicy()
    methods = [m for m in dir(svc) if not m.startswith("_") and callable(getattr(svc, m))]
    for m in methods:
        assert "execute" not in m.lower()
        assert "run" not in m.lower()
        assert "call" not in m.lower()


def test_disclaimer_present():
    """select result includes disclaimer about non-execution."""
    result = ToolSelectionPolicy.select(["read_file"], "测试")
    assert "不执行" in result["disclaimer"] or "不" in result["disclaimer"]
