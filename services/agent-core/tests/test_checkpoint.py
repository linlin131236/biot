from bolt_core.checkpoint import CheckpointService, Checkpoint
from bolt_core.review_gate import ReviewGate, ReviewChecklist


def test_checkpoint_create_and_load(tmp_path):
    svc = CheckpointService(workspace=str(tmp_path))
    cp = svc.create(run_id="run_001", goal_id="goal_abc12345",
                    changed_files=["app.py", "test_app.py"])

    assert cp.run_id == "run_001"
    assert "app.py" in cp.changed_files

    loaded = svc.load(cp.id)
    assert loaded is not None
    assert loaded.run_id == "run_001"


def test_checkpoint_does_not_copy_large_files(tmp_path):
    svc = CheckpointService(workspace=str(tmp_path))
    # Create a large file
    big = tmp_path / "big.bin"
    big.write_bytes(b"x" * (10 * 1024 * 1024))  # 10MB

    cp = svc.create(run_id="run_002", goal_id="goal_def67890",
                    changed_files=["big.bin"])
    # Checkpoint should not include large files
    assert "big.bin" not in (cp.file_contents or {})


def test_checkpoint_no_secrets(tmp_path):
    svc = CheckpointService(workspace=str(tmp_path))
    cp = svc.create(run_id="run_003", goal_id="goal_ghi11111",
                    changed_files=[])
    # Metadata should not contain secrets
    d = cp.to_dict()
    values_str = str(d)
    assert "sk-" not in values_str


def test_resume_context_includes_constraints(tmp_path):
    svc = CheckpointService(workspace=str(tmp_path))
    cp = svc.create(run_id="run_004", goal_id="goal_jkl22222",
                    changed_files=[],
                    constraints=["no external deps", "read_only"])
    loaded = svc.load(cp.id)
    assert "no external deps" in loaded.constraints


def test_resume_pending_permission_remains_pending(tmp_path):
    svc = CheckpointService(workspace=str(tmp_path))
    cp = svc.create(run_id="run_005", goal_id="goal_mno33333",
                    changed_files=[],
                    pending_permissions=["file_write:app.py"])
    loaded = svc.load(cp.id)
    assert "file_write:app.py" in loaded.pending_permissions


def test_review_gate_fail_blocks_continuation():
    gate = ReviewGate()
    checklist = ReviewChecklist(
        items=["All tests pass", "No security issues", "Code reviewed"])

    # Fail one item
    result = gate.evaluate(checklist, results={
        "All tests pass": True,
        "No security issues": False,
        "Code reviewed": True,
    })
    assert not result.passed
    assert "No security issues" in result.failures


def test_review_gate_pass():
    gate = ReviewGate()
    checklist = ReviewChecklist(
        items=["Tests pass", "Build passes"])
    result = gate.evaluate(checklist, results={
        "Tests pass": True,
        "Build passes": True,
    })
    assert result.passed


def test_review_gate_incomplete_items_fail():
    gate = ReviewGate()
    checklist = ReviewChecklist(items=["A", "B", "C"])
    result = gate.evaluate(checklist, results={"A": True})
    assert not result.passed
    assert len(result.failures) >= 2  # B and C missing


def test_project_status_local_commits(tmp_path):
    svc = CheckpointService(workspace=str(tmp_path))
    status = svc.project_status()
    assert "commits" in status
    assert "uncommitted_changes" in status
