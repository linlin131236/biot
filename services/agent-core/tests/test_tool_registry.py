"""Tests for ToolRegistry – registration, query, filtering, duplicate blocking."""
import pytest

from bolt_core.tool_registry import (
    CATEGORY_DANGEROUS,
    CATEGORY_READ_ONLY,
    CATEGORY_WRITE,
    PERM_DANGEROUS,
    PERM_NONE,
    RISK_HIGH,
    ToolDef,
    ToolRegistry,
)


# ── Helpers ──

def make_tool(tool_id="test_tool", **overrides) -> ToolDef:
    defaults = {
        "tool_id": tool_id,
        "display_name": "测试工具",
        "category": CATEGORY_READ_ONLY,
        "description": "用于测试的工具",
        "permission_required": PERM_NONE,
        "allow_auto_run": True,
        "risk_level": "low",
    }
    defaults.update(overrides)
    return ToolDef(**defaults)


# ── ToolDef validation ──

class TestToolDef:
    def test_valid_tool_def(self):
        t = make_tool()
        assert t.tool_id == "test_tool"
        assert t.display_name == "测试工具"
        assert t.category == CATEGORY_READ_ONLY

    def test_empty_tool_id_raises(self):
        with pytest.raises(ValueError, match="tool_id 不能为空"):
            make_tool(tool_id="")

    def test_invalid_category_raises(self):
        with pytest.raises(ValueError, match="未知工具类别"):
            make_tool(category="invalid_cat")

    def test_invalid_permission_raises(self):
        with pytest.raises(ValueError, match="未知权限等级"):
            make_tool(permission_required="super_admin")

    def test_invalid_risk_level_raises(self):
        with pytest.raises(ValueError, match="未知风险等级"):
            make_tool(risk_level="extreme")

    def test_to_dict_contains_all_keys(self):
        d = make_tool().to_dict()
        assert d["tool_id"] == "test_tool"
        assert d["display_name"] == "测试工具"
        assert d["category"] == CATEGORY_READ_ONLY
        assert "category_label" in d
        assert "permission_label" in d
        assert "risk_label" in d

    def test_defaults_allow_auto_run_false(self):
        t = ToolDef(tool_id="x", display_name="X", category=CATEGORY_READ_ONLY, description="d")
        assert t.allow_auto_run is False

    def test_default_permission_none(self):
        t = ToolDef(tool_id="x", display_name="X", category=CATEGORY_READ_ONLY, description="d")
        assert t.permission_required == PERM_NONE


# ── ToolRegistry register ──

class TestRegister:
    def test_register_adds_tool(self):
        r = ToolRegistry()
        r.register(make_tool("t1"))
        assert len(r) == 1

    def test_register_duplicate_id_raises(self):
        r = ToolRegistry()
        r.register(make_tool("dup"))
        with pytest.raises(ValueError, match="已注册"):
            r.register(make_tool("dup", display_name="重复工具"))

    def test_register_returns_tool_def(self):
        r = ToolRegistry()
        t = make_tool("ret")
        result = r.register(t)
        assert result is t


# ── ToolRegistry get ──

class TestGet:
    def test_get_existing(self):
        r = ToolRegistry()
        r.register(make_tool("exists"))
        t = r.get("exists")
        assert t is not None
        assert t.tool_id == "exists"

    def test_get_missing(self):
        r = ToolRegistry()
        assert r.get("nope") is None


# ── ToolRegistry list ──

class TestList:
    def test_list_all(self):
        r = ToolRegistry()
        r.register(make_tool("a"))
        r.register(make_tool("b"))
        assert len(r.list()) == 2

    def test_list_sorted_by_id(self):
        r = ToolRegistry()
        r.register(make_tool("z"))
        r.register(make_tool("a"))
        ids = [t.tool_id for t in r.list()]
        assert ids == ["a", "z"]

    def test_list_filter_by_category(self):
        r = ToolRegistry()
        r.register(make_tool("r", category=CATEGORY_READ_ONLY))
        r.register(make_tool("w", category=CATEGORY_WRITE))
        result = r.list(category=CATEGORY_READ_ONLY)
        assert len(result) == 1
        assert result[0].tool_id == "r"

    def test_list_invalid_category_raises(self):
        r = ToolRegistry()
        with pytest.raises(ValueError, match="未知工具类别"):
            r.list(category="nope")


# ── ToolRegistry unregister ──

class TestUnregister:
    def test_unregister_existing(self):
        r = ToolRegistry()
        r.register(make_tool("rm"))
        assert r.unregister("rm") is True
        assert len(r) == 0

    def test_unregister_missing(self):
        r = ToolRegistry()
        assert r.unregister("nope") is False


# ── ToolRegistry summary ──

class TestSummary:
    def test_summary_empty(self):
        r = ToolRegistry()
        s = r.summary()
        assert s["total"] == 0

    def test_summary_counts(self):
        r = ToolRegistry()
        r.register(make_tool("r1", category=CATEGORY_READ_ONLY))
        r.register(make_tool("r2", category=CATEGORY_READ_ONLY))
        r.register(make_tool("w1", category=CATEGORY_WRITE, allow_auto_run=False))
        s = r.summary()
        assert s["total"] == 3
        assert s["counts_by_category"][CATEGORY_READ_ONLY] == 2
        assert s["counts_by_category"][CATEGORY_WRITE] == 1
        assert s["allow_auto_run_counts"].get(CATEGORY_READ_ONLY, 0) == 2
        assert CATEGORY_WRITE not in s["allow_auto_run_counts"]


# ── ToolDef category/permission/risk ──

class TestCategories:
    def test_dangerous_tool_no_auto_run(self):
        t = make_tool("d", category=CATEGORY_DANGEROUS, allow_auto_run=False, risk_level=RISK_HIGH)
        assert t.allow_auto_run is False
        assert t.risk_level == RISK_HIGH

    def test_unknown_tool_no_auto_run(self):
        t = ToolDef(tool_id="u", display_name="未知", category="unknown", description="未知工具",
                    allow_auto_run=False, risk_level="high")
        assert t.allow_auto_run is False

    def test_write_tool_needs_permission(self):
        t = make_tool("w", category=CATEGORY_WRITE, permission_required=PERM_DANGEROUS)
        assert t.permission_required == PERM_DANGEROUS

    def test_tool_equality(self):
        """Frozen dataclass equality works even though dict fields block hashing."""
        t1 = make_tool("h")
        t2 = make_tool("h")
        assert t1 == t2
        assert t1 is not t2
