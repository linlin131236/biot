"""Unit tests for PlannerTaskGraphService. Planning only, no auto-execution."""
import pytest

from bolt_core.planner_task_graph import PlannerTaskGraphService


def test_create_graph_returns_dict():
    """create_graph returns a dict with id, title, objective, nodes."""
    svc = PlannerTaskGraphService()
    g = svc.create_graph("测试图", "测试目标")
    assert g["id"].startswith("graph_")
    assert g["title"] == "测试图"
    assert g["objective"] == "测试目标"
    assert g["nodes"] == []


def test_list_graphs_returns_summaries():
    """list_graphs returns summary list."""
    svc = PlannerTaskGraphService()
    svc.create_graph("图1", "目标1")
    svc.create_graph("图2", "目标2")
    summaries = svc.list_graphs()
    assert len(summaries) == 2
    for s in summaries:
        assert "id" in s
        assert "title" in s
        assert "node_count" in s


def test_add_node_returns_node_dict():
    """add_node adds a node and returns its dict."""
    svc = PlannerTaskGraphService()
    g = svc.create_graph("测试", "目标")
    node = svc.add_node(g["id"], "节点1")
    assert node["id"].startswith("node_")
    assert node["title"] == "节点1"
    assert node["status"] == "pending"


def test_add_node_with_dependency():
    """Node can be added with dependency on existing node."""
    svc = PlannerTaskGraphService()
    g = svc.create_graph("测试", "目标")
    n1 = svc.add_node(g["id"], "前置节点")
    n2 = svc.add_node(g["id"], "后置节点", dependencies=[n1["id"]])
    assert n2["dependencies"] == [n1["id"]]


def test_add_node_with_invalid_dependency_raises():
    """Adding node with non-existent dependency raises ValueError."""
    svc = PlannerTaskGraphService()
    g = svc.create_graph("测试", "目标")
    with pytest.raises(ValueError, match="dependency node not found"):
        svc.add_node(g["id"], "孤儿节点", dependencies=["nonexistent"])


def test_add_node_with_invalid_risk_raises():
    """Invalid risk value raises ValueError."""
    svc = PlannerTaskGraphService()
    g = svc.create_graph("测试", "目标")
    with pytest.raises(ValueError, match="invalid risk"):
        svc.add_node(g["id"], "节点", risk="extreme")


def test_add_node_with_invalid_role_raises():
    """Invalid owner_role raises ValueError."""
    svc = PlannerTaskGraphService()
    g = svc.create_graph("测试", "目标")
    with pytest.raises(ValueError, match="invalid owner_role"):
        svc.add_node(g["id"], "节点", owner_role="ceo")


def test_update_node_status_valid_transition():
    """Valid status transition succeeds."""
    svc = PlannerTaskGraphService()
    g = svc.create_graph("测试", "目标")
    node = svc.add_node(g["id"], "节点1")
    updated = svc.update_node_status(g["id"], node["id"], "in_progress")
    assert updated["status"] == "in_progress"


def test_update_node_status_invalid_transition():
    """Invalid status transition raises ValueError."""
    svc = PlannerTaskGraphService()
    g = svc.create_graph("测试", "目标")
    node = svc.add_node(g["id"], "节点1")
    # pending -> completed is not allowed directly
    with pytest.raises(ValueError, match="invalid status transition"):
        svc.update_node_status(g["id"], node["id"], "completed")


def test_update_node_status_completed_is_terminal():
    """Completed nodes cannot change status."""
    svc = PlannerTaskGraphService()
    g = svc.create_graph("测试", "目标")
    node = svc.add_node(g["id"], "节点1")
    svc.update_node_status(g["id"], node["id"], "in_progress")
    svc.update_node_status(g["id"], node["id"], "completed")
    with pytest.raises(ValueError, match="invalid status transition"):
        svc.update_node_status(g["id"], node["id"], "in_progress")


def test_cannot_start_with_unmet_dependency():
    """Cannot start a node if its dependency is not completed."""
    svc = PlannerTaskGraphService()
    g = svc.create_graph("测试", "目标")
    n1 = svc.add_node(g["id"], "前置节点")
    n2 = svc.add_node(g["id"], "后置节点", dependencies=[n1["id"]])
    with pytest.raises(ValueError, match="not completed"):
        svc.update_node_status(g["id"], n2["id"], "in_progress")


def test_can_start_after_dependency_completed():
    """Can start node after dependency is completed."""
    svc = PlannerTaskGraphService()
    g = svc.create_graph("测试", "目标")
    n1 = svc.add_node(g["id"], "前置节点")
    n2 = svc.add_node(g["id"], "后置节点", dependencies=[n1["id"]])
    svc.update_node_status(g["id"], n1["id"], "in_progress")
    svc.update_node_status(g["id"], n1["id"], "completed")
    updated = svc.update_node_status(g["id"], n2["id"], "in_progress")
    assert updated["status"] == "in_progress"


def test_get_graph_nonexistent():
    """Getting non-existent graph returns None."""
    svc = PlannerTaskGraphService()
    assert svc.get_graph("nonexistent") is None


def test_add_node_nonexistent_graph():
    """Adding node to non-existent graph raises ValueError."""
    svc = PlannerTaskGraphService()
    with pytest.raises(ValueError, match="graph not found"):
        svc.add_node("nonexistent", "节点")


def test_no_auto_execution():
    """Service has no execution methods - only planning/status management."""
    svc = PlannerTaskGraphService()
    # No method should call git, shell, subprocess, or harness
    method_names = [m for m in dir(svc) if not m.startswith("_")]
    execution_methods = ["execute", "run", "start", "deploy", "approve"]
    for name in method_names:
        for exec_word in execution_methods:
            assert exec_word not in name, f"unexpected execution method: {name}"
