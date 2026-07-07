from bolt_core.harness import Harness


def test_harness_has_internal_state_lock(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    harness = Harness(workspace=str(workspace))

    assert hasattr(harness, "_state_lock")
