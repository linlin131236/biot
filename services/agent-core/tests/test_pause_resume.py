"""Unit tests for PauseResumeService. Manages pause lifecycle, never auto-executes."""
import pytest

from bolt_core.pause_resume import PauseResumeService


def test_pause_from_running():
    """Pause from running state succeeds."""
    svc = PauseResumeService()
    result = svc.pause("node_1", "running", "用户需要暂停检查")
    assert result["action"] == "paused"
    assert result["to_status"] == "paused"
    assert svc.is_paused("node_1") is True


def test_pause_from_ready():
    """Pause from ready state succeeds."""
    svc = PauseResumeService()
    result = svc.pause("node_2", "ready", "前置检查")
    assert result["action"] == "paused"


def test_pause_from_completed_raises():
    """Cannot pause a completed node."""
    svc = PauseResumeService()
    with pytest.raises(ValueError, match="只能从"):
        svc.pause("node_3", "completed")


def test_pause_from_pending_raises():
    """Cannot pause a pending node."""
    svc = PauseResumeService()
    with pytest.raises(ValueError, match="只能从"):
        svc.pause("node_4", "pending")


def test_double_pause_raises():
    """Pausing an already-paused node raises error."""
    svc = PauseResumeService()
    svc.pause("node_5", "running")
    with pytest.raises(ValueError, match="已经在暂停状态"):
        svc.pause("node_5", "running")


def test_resume_restores_ready():
    """Resume returns node to ready state with checks."""
    svc = PauseResumeService()
    svc.pause("node_6", "running", "暂停测试")
    result = svc.resume("node_6")
    assert result["action"] == "resumed"
    assert result["to_status"] == "ready"
    assert len(result["checks"]) >= 2


def test_resume_requires_human_decision():
    """Resume marks requires_human_decision when recheck_permissions=True."""
    svc = PauseResumeService()
    svc.pause("node_7", "running")
    result = svc.resume("node_7", recheck_permissions=True)
    assert result["requires_human_decision"] is True


def test_resume_nonexistent_raises():
    """Resuming a non-paused node raises error."""
    svc = PauseResumeService()
    with pytest.raises(ValueError, match="不在暂停状态"):
        svc.resume("nonexistent")


def test_resume_clears_paused_state():
    """After resume, node is no longer paused."""
    svc = PauseResumeService()
    svc.pause("node_8", "running")
    svc.resume("node_8")
    assert svc.is_paused("node_8") is False


def test_cancel_pause_marks_failed():
    """Cancel pause transitions node to failed."""
    svc = PauseResumeService()
    svc.pause("node_9", "running", "测试取消")
    result = svc.cancel_pause("node_9")
    assert result["action"] == "cancelled"
    assert result["to_status"] == "failed"
    assert svc.is_paused("node_9") is False


def test_get_paused_nodes():
    """get_paused_nodes returns list of paused node IDs."""
    svc = PauseResumeService()
    svc.pause("a", "running")
    svc.pause("b", "ready")
    paused = svc.get_paused_nodes()
    assert set(paused) == {"a", "b"}


def test_snapshot_stores_evidence():
    """Pause snapshot stores evidence refs."""
    svc = PauseResumeService()
    result = svc.pause("node_10", "running", evidence_refs=["ev_1", "ev_2"])
    snapshot = result["snapshot"]
    assert snapshot["evidence_refs"] == ["ev_1", "ev_2"]


def test_pause_includes_warning():
    """Pause result includes warning about side effects."""
    svc = PauseResumeService()
    result = svc.pause("node_11", "running", "测试")
    assert "暂停期间" in result["warning"] or "副作用" in result["warning"]


def test_resume_includes_warning():
    """Resume result includes warning about PermissionGate."""
    svc = PauseResumeService()
    svc.pause("node_12", "running")
    result = svc.resume("node_12")
    assert "PermissionGate" in result["warning"] or "权限" in result["warning"]


def test_no_auto_execution():
    """PauseResumeService has no execute/run/approve methods."""
    svc = PauseResumeService()
    methods = [m for m in dir(svc) if not m.startswith("_") and callable(getattr(svc, m))]
    for m in methods:
        assert "execute" not in m.lower()
        assert "approve" not in m.lower()
