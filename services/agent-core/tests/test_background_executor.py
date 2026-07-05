from bolt_core.background_executor import BackgroundExecutor


def test_background_spawn_and_poll(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    executor = BackgroundExecutor(str(workspace))

    result = executor.spawn("echo hello", str(workspace))

    assert result.status == "running"
    assert result.session_id.startswith("bg_")

    import time
    time.sleep(0.5)

    poll = executor.poll(result.session_id)
    assert poll.status in ("completed", "running")
    assert poll.session_id == result.session_id


def test_background_kill(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    executor = BackgroundExecutor(str(workspace))

    result = executor.spawn("ping -n 10 127.0.0.1", str(workspace))
    assert result.status == "running"

    killed = executor.kill(result.session_id)
    assert killed.status == "killed"
    assert killed.session_id == result.session_id


def test_background_poll_unknown_session(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    executor = BackgroundExecutor(str(workspace))

    result = executor.poll("nonexistent")
    assert result.status == "unknown"


def test_background_kill_unknown_session(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    executor = BackgroundExecutor(str(workspace))

    result = executor.kill("nonexistent")
    assert result.status == "unknown"


def test_background_spawn_invalid_workdir(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    executor = BackgroundExecutor(str(workspace))

    result = executor.spawn("echo hi", "/nonexistent/path")
    assert result.status == "failed"


def test_background_list_sessions(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    executor = BackgroundExecutor(str(workspace))

    executor.spawn("echo a", str(workspace))
    executor.spawn("echo b", str(workspace))

    sessions = executor.list_sessions()
    assert len(sessions) >= 2
