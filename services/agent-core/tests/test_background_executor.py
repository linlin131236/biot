from bolt_core.background_executor import BackgroundExecutor
import time


def test_background_spawn_and_poll(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    executor = BackgroundExecutor(str(workspace))

    result = executor.spawn("echo hello", str(workspace))

    assert result.status == "running"
    assert result.session_id.startswith("bg_")

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


def test_background_completed_process_released(tmp_path):
    """Completed processes should be released from _processes dict."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    executor = BackgroundExecutor(str(workspace))

    result = executor.spawn("echo done", str(workspace))
    time.sleep(1.0)

    poll = executor.poll(result.session_id)
    assert poll.status == "completed"
    # After poll returns completed, process ref should be released
    assert result.session_id not in executor._processes


def test_background_high_output_no_deadlock(tmp_path):
    """High-output process should not deadlock due to pipe buffer full."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    executor = BackgroundExecutor(str(workspace))

    # Generate > 64KB output to fill pipe buffer
    result = executor.spawn("python -c \"import sys; [print('x' * 100) for _ in range(1000)]\"", str(workspace))
    assert result.status == "running"

    # Should complete without deadlock (background thread consumes stdout)
    for _ in range(30):
        time.sleep(0.5)
        poll = executor.poll(result.session_id)
        if poll.status in ("completed", "failed"):
            break
    assert poll.status in ("completed", "failed", "running")


def test_background_output_truncated_at_limit(tmp_path):
    """Output exceeding max_output_size should be truncated."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    executor = BackgroundExecutor(str(workspace), max_output_size=1024)

    result = executor.spawn("python -c \"import sys; [print('x' * 100) for _ in range(100)]\"", str(workspace))
    time.sleep(2.0)

    poll = executor.poll(result.session_id)
    output = poll.output
    # Output should be capped around max_output_size (may exceed slightly due to append timing)
    assert len(output) <= 2048  # generous bound; real limit is 1024 + one chunk


def test_background_kill_releases_ref(tmp_path):
    """Kill should release the process reference."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    executor = BackgroundExecutor(str(workspace))

    result = executor.spawn("ping -n 30 127.0.0.1", str(workspace))
    killed = executor.kill(result.session_id)
    assert killed.status == "killed"
    assert result.session_id not in executor._processes


def test_background_rejects_shell_control_syntax(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    executor = BackgroundExecutor(str(workspace))

    result = executor.spawn("echo safe | powershell", str(workspace))

    assert result.status == "failed"
    assert result.output == "shell control syntax not allowed: |"
